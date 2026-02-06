import json
from vector_db import update_point_sync, get_point_sync
from llm import responses_sync, prompt_template
import json
import logging
from background_tasks import celery_app
import dotenv
import os
from typing import List

dotenv.load_dotenv()

OLLAMA_INDEXING_AGENT_MODEL = os.environ.get('OLLAMA_INDEXING_AGENT_MODEL')

logger = logging.getLogger(__name__)

############################################## AUDIT CHUNK AGENT ###############################################

AUDIT_CHUNK_SYSTEM_PROMPT = """
only return JSON formatted response not markdown no extra text.

only respond with the following JSON formats:
{"audit": "True|False", "additional_context": "...", "reasoning": "..."}
set audit to true if need to be audited or false to keep current text
"""

AUDIT_CHUNK_PROMPT = """
You are enriching a text chunk from a RAG document to make it self-contained and understandable on its own by adding additional context.
Make the targeted chunk text understandable WITHOUT reading other chunks by adding short information from Previous text chunk.
Return additional context to support the targeted text chunk. dont mention about targeted chunk or previous chunk on the result.

CRITICAL RULES:
1. Return at most 2 sentences.
2. Only add what is strictly necessary so the targeted chunk make sense.
3. If the targeted chunk already make sense, return audit=False.
4. Prefer copying exact entity names/titles from Previous when available.
5. Add document summary if you found it.
6. Add section information about the targeted chunk if you found it.
7. Sdd entity, date and document section or other context if you found and relevant
8. Never change original chunk text on audited chunk, only add additional context.

{addtional_prompt}

Previous original chunk text:
{previous_original_chunk_text}

Targeted audited chunk text:
{targeted_audited_chunk_text}

Targeted original chunk text:
{targeted_original_chunk_text}
"""

VECTOR_DB_TOOLS = [
{
    "tool_name": "get_point",
    "description": "use for retrieving a text chunk from the vector database",
    "argument": {
        "chunk_id": "string with format: {tenant}:{document_id}:{chunk_index}",
        "collection_name": "string format: tenants_{tenant}_documents"
    }
}]

def safe_json_loads(content:str) -> dict:
    """
    This function is for handling string returned by agent converting it to dict can be used by the function
    """
    try:
        content.strip()
        return json.loads(content)
    except:
        content = content.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1:
                raise ValueError(f"No JSON found in model output:\n{content}")
            return json.loads(content[start:end+1])

def background_audit_chunks(tenant, doc_id, num_chunks):
    for chunk_idx in range(num_chunks):
        audit_chunk.delay(tenant=tenant, doc_id=doc_id, chunk_idx=chunk_idx)

@celery_app.task(name="audit_chunk", bind=True)
def audit_chunk(self, tenant:str, doc_id:str, chunk_idx:int, addtional_prompt:str=""):
    """
    This agent will iterate every previous chunks and 1 next chunk to add more context to original text chunk
    """
    current_chunk_id = f"{tenant}:{doc_id}:{chunk_idx}"
    collection_name = f"tenants_{tenant}_documents"

    system_prompt = prompt_template(AUDIT_CHUNK_SYSTEM_PROMPT, {})

    logger.info(f"auditing {current_chunk_id}")
    audit = False
    for id in [*range(chunk_idx, 0, -1), chunk_idx+1]:
        targeted_chunk = get_point_sync(chunk_id=current_chunk_id, collection_name=collection_name)
        targeted_chunk_payload = targeted_chunk[0].payload
        targeted_original_chunk_text = targeted_chunk_payload.get("original_text", "")
        targeted_audited_chunk_text = targeted_chunk_payload.get("audited_text", "")

        previous_chunk_id = f"{tenant}:{doc_id}:{id}"

        logger.info(f"analyzing {previous_chunk_id}")
        
        try:
            previous_chunk = get_point_sync(
                chunk_id=previous_chunk_id, 
                collection_name=collection_name
            )
        except Exception as e:
            if id == chunk_idx+1:
                logger.error(f"found error, next chunk may not exist: {e}")
            else:
                logger.error(f"found error while getting chunk with error detail: {e}")
            continue

        previous_original_chunk_text = previous_chunk[0].payload.get("original_text", "")
        agent_prompt = prompt_template(AUDIT_CHUNK_PROMPT, {
            "previous_original_chunk_text": previous_original_chunk_text,
            "targeted_audited_chunk_text": targeted_audited_chunk_text,
            "targeted_original_chunk_text": targeted_original_chunk_text,
            "addtional_prompt": addtional_prompt
        })

        message = [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": agent_prompt
        }]

        response = responses_sync(message=message, model=OLLAMA_INDEXING_AGENT_MODEL)

        action = safe_json_loads(response['message']['content'])

        logger.info("action: %s", action)

        if action["audit"] in ['True', 1, "true"]:
            action['update_point'] = {
                "chunk_id": f"{current_chunk_id}",
                "collection_name": f"{collection_name}",
                "payload": {
                    "chunk_id": f"{current_chunk_id}",
                    "tenant": tenant,
                    "doc_id": doc_id,
                    "index": chunk_idx,
                    "title": targeted_chunk_payload.get("title", ""),
                    "text": targeted_chunk_payload.get("text", ""),
                    "original_text": targeted_chunk_payload.get("original_text", ""),
                    "audited_text": f"{targeted_chunk_payload.get('audited_text', '')}\n\n{action.get('additional_context', '')}",
                    "audit_status": targeted_chunk_payload.get("audit_status", ""),
                    "audit_version": targeted_chunk_payload.get("audit_version", "")
                }
            }
            update_point_sync(**action["update_point"])
            audit = True

            logger.info("Audited text updated")
        else:
            logger.info("No need to update text")
        
    if audit:
        targeted_chunk = get_point_sync(chunk_id=current_chunk_id, collection_name=collection_name)
        targeted_chunk_payload = targeted_chunk[0].payload
        action['update_point'] = {
                "chunk_id": f"{current_chunk_id}",
                "collection_name": f"{collection_name}",
                "payload": {
                    "chunk_id": f"{current_chunk_id}",
                    "tenant": tenant,
                    "doc_id": doc_id,
                    "index": chunk_idx,
                    "title": targeted_chunk_payload.get("title", ""),
                    "text": f"{targeted_chunk_payload.get('audited_text', '')}\n{targeted_chunk_payload['original_text']}",
                    "original_text": targeted_chunk_payload.get("original_text", ""),
                    "audited_text": targeted_chunk_payload.get("audited_text", ""),
                    "audit_status":"audited",
                    "audit_version": str(int(targeted_chunk_payload.get("audit_version", 0) or 0) + 1)
                }
            }
        update_point_sync(**action["update_point"])

    return {"audit": "finish"}
   


############################################## RITRIVAL EVALUATION AGENT ###############################################
RITRIVAL_EVALUATION_SYSTEM_PROMPT = """
only return JSON formatted response not markdown no extra text.

only respond with the following JSON formats:
{"audit": "True|False", "additional_prompt": "...", "audit_agent_args": [{...}, {...}], "reasoning": "..."}

audit_agent_args is the list of arguments to be sent to audit agent for each chunk that need to be audited
format audit_agent_args:
{"tenant": "...", "doc_id": "...", "chunk_idx": ...}

set audit to true if need to be audited or false to keep current text
additional_prompt is the instruction sent to audit agent to improve the chunk context
"""

RITRIVAL_EVALUATION_PROMPT = """
You are evaluating ritrival quality between two text chunks from a RAG document to make sure the targeted chunk is self-contained and understandable on its own by adding additional context.

Audit if:
1. the ritrived document contain contain unclear chunk context
2. the ritrived document is not relevant to question context
3. multiples chunk look similar it means the chunk need more context to be unique
4. the ritrived document have high score but not relevant to question context
5. the ritrived document miss important context to understand the question
6. the ritrived document is not helping question to be more understandable
7. the ritrived document is not adding any value to question
8. the ritrived document have high score but not answerable

Question:
{question}

Ritrived Document:
{ritrived_document}
"""

@celery_app.task(name="evaluate_chunk", bind=True)
def background_evaluation_agent(self, question:str, documents:List[dict]):
    """
    This agent will evaluate every ritrived chunks to add more context to original text chunk
    """
    logger.info("Starting evaluation of ritrived documents")

    system_prompt = prompt_template(RITRIVAL_EVALUATION_SYSTEM_PROMPT, {})

    agent_prompt = prompt_template(RITRIVAL_EVALUATION_PROMPT, {
        "question": question,
        "ritrived_document": documents
    })

    message = [{
        "role": "system",
        "content": system_prompt
    }, {
        "role": "user",
        "content": agent_prompt
    }]

    response = responses_sync(message=message, model=OLLAMA_INDEXING_AGENT_MODEL)

    action = safe_json_loads(response['message']['content'])

    logger.info("action: %s", action)

    if action["audit"] in ['True', 1, "true"]:
        for chunk_args in action["audit_agent_args"]:
            try:
                audit_chunk().delay(**chunk_args)
            except Exception as e:
                logger.error(f"Error scheduling audit chunk for {chunk_args['chunk_idx']}: {e}")

        logger.info("Evaluation chunk audit sent to audit agent")
    else:
        logger.info("No need to update chunk")

    return {"evaluation": "finish"}