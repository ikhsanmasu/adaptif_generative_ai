from agent import chat_agent
from chat_history import add_chat_history
from fastapi import HTTPException
import logging
import os
import dotenv

dotenv.load_dotenv()

OLLAMA_CHAT_MODEL = os.environ.get('OLLAMA_CHAT_MODEL')

logger = logging.getLogger(__name__)

async def chat_completion(message:str, tenant:str, user_id:str, model:str = OLLAMA_CHAT_MODEL, max_tokens:int = 1024, temperature:float = 0.2) -> dict:    
    try: 
        agent_responses = await chat_agent(message=message, tenant=tenant, user_id=user_id, model=model)

        try:
            await add_chat_history(tenant, user_id, {
                "role": "user",
                "content": message
            })
            
            await add_chat_history(tenant, user_id, {
                "role": "assistant",
                "content": agent_responses['final_answer']
            })
        except Exception as e:
            logger.error(f"Error Found with detail: {e}")

        result = {
            "question": message,
            "answer": agent_responses['final_answer'],
            "ritrieved_documents": agent_responses['final_documents'],
            "prompt_used": agent_responses['final_prompt'],
            "token_usage_estimation": agent_responses['token_usage_estimation']
        }
        return result
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(500)


