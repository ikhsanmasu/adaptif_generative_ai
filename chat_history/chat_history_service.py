import redis
import dotenv
import os
import json
import logging

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

async def add_chat_history(tenant:str, user_id:str, value:dict):
    try:
        key = f"chat_history:{tenant}:{user_id}"
        value = json.dumps(value)
        redis_client.rpush(key, value)
        redis_client.ltrim(key, -20, -1)
        redis_client.expire(key, 24 * 3600)

        logger.info(f"Add new chat history with key: ${key}, value: ${value}")
    except Exception as e:
        raise Exception(f"failed to add new chat history with error: {e}")

async def get_chat_history(tenant:str, user_id:str, limit):
    key = f"chat_history:{tenant}:{user_id}"
    try:
        history_raw = redis_client.lrange(key, -limit, -1)
        return [json.loads(buble) for buble in history_raw]
    except:
        raise Exception(f"failed to geyt chat history with error: {e}")