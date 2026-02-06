import json
from vector_db import search_documents
from llm import responses, prompt_template
import json
from chat_history import get_chat_history
import logging
from agent import background_evaluation_agent

logger = logging.getLogger(__name__)

AUDIT_CHUNK_AGENT_SYSTEM_PROMPT = """
you are a tool using agent.
only return JSON formatted response not markdown no extra text.

tools you can use:
{tools_list}

only respond in one of the following JSON formats:
1) tool call:
a. get document
{"type": "tool_call", "tool_name": "search_documents"|"get_chat_history", "arguments": {...}, "reasoning": "..."}

2) final:
only call if you finish
{"type": "final", "final_answer":"...", "final_search_document_arguments":"..."}
fill final_search_document_arguments if context found and used, else fill with empty string ""

if you found an error while using the tools, don't mention to user.
"""

AUDIT_CHUNK_AGENT_PROMPT = """
You are a chat bot agent that answer question with context provided by document

ritrieve document until you make sure get the right context to answer the question.
decide the query text to ritrieve document to get better result and give why you deciced on reasoning
decide number of limit document to be ritrieved based on the question and give why you deciced on reasoning
document are chunking smally so you can start with big limit

only use ritrieval tool if you need, if you can answer right away dont use it.

you also can use chat history tool to understand what user question context about.

user tenant:
{tenant}
user id:
{user_id}
user question:
{query}
"""


VECTOR_DB_TOOLS = [
    {
    "tool_name": "search_documents",
    "description": "use for retrieving document from the vector database",
    "argument": {
        "query": "string of the question you can adjust",
        "tenant": "string of user tenant",
        "limit": "int of document limit ritrival you can adjust"
        }
    },
    {
    "tool_name": "get_chat_history",
    "description": "use for geting chat history",
    "argument": {
        "tenant": "string of user tenant",
        "user_id": "string of user id",
        "limit": "int of latest n chat history"
        }
    }
]

TOOLS = {
    "search_documents": search_documents,
    "get_chat_history": get_chat_history
}

def safe_json_loads(content: str):
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
    
# for higher model usage
async def chat_agent(message, tenant, user_id, model) -> str:
    logger.info("agent chat starting")
    system_prompt = prompt_template(AUDIT_CHUNK_AGENT_SYSTEM_PROMPT, {
        "tools_list": str(VECTOR_DB_TOOLS)
    })

    agent_prompt = prompt_template(AUDIT_CHUNK_AGENT_PROMPT, {
        "tenant": tenant,
        "user_id": user_id,
        "query": message
    })

    message = [{
        "role": "system",
        "content": system_prompt
    }, {
        "role": "user",
        "content": agent_prompt
    }]

    
    final_answer = ""
    final_document = []
    token_usage_estimation = 0

    attempt = 0
    limit_attempt = 15
    while attempt < limit_attempt:
        attempt += 1
        logger.info(f"attempt {attempt}")

        content = await responses(message=message, model=model)
        token_usage_estimation += content.eval_count

        action = safe_json_loads(content['message']['content'])
        logger.info("action:", action)

        if action["type"] == "tool_call":
            try:
                tool_result = await TOOLS[action["tool_name"]](**action["arguments"])

                document = ""
                if action["tool_name"] == "search_documents":
                    for chunk in tool_result:
                        document += \
                            f"score: {chunk.score}\n" \
                            + f"title: {chunk.payload.get("title", "")}\n" \
                            + f"text: {chunk.payload.get("text", "")}\n"
            except Exception as e:
                document = f"Error Happen when ritrieving document with detail: {e}"

            message.append({
                "role": "assistant",
                "content": json.dumps(action)
            })
            message.append({
                "role": "user",
                "content": json.dumps({
                    "tool_name": action["tool_name"],
                    "arguments": action["arguments"],
                    "tool_result": document if action["tool_name"] == "search_documents" else tool_result
                    })
            })
            logger.info(f"Tool called: {action["tool_name"]}, with arguments: {action["arguments"]}")
            
        elif action["type"] == "final":
            logger.info("Chat Agent Finish")
            final_answer = action["final_answer"]
            if action["final_search_document_arguments"]:
                try:
                    final_document = await TOOLS[action["search_documents"]](**action["final_search_document_arguments"])
                except:
                    final_document = []
            break
    
    background_evaluation_agent.delay(question=message, document=final_document)

    logger.info("agent chat stop")
    return {"final_answer": final_answer, "final_documents": final_document, "final_prompt": message, "token_usage_estimation": token_usage_estimation}