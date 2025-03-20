import os
from dotenv import load_dotenv
import redis

load_dotenv()

def redis_config():
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT"))
    REDIS_DATABASE = int(os.getenv("REDIS_DATABASE"))
    
    try:
        rd = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DATABASE)
        rd.ping()
        print("Redis connected successfully")
        return rd
    except redis.ConnectionError as e:
        print(f"Redis connection failed: {e}")
        return None

    