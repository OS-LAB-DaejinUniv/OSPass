### REDIS 사용 ###
### POSTGRESQL 사용 ###

import os
from dotenv import load_dotenv
import redis
import logging


load_dotenv()

def redis_config():
    
    try:
        REDIS_HOST : str = os.getenv("REDIS_HOST")
        REDIS_PORT : int = os.getenv("REDIS_PORT")
        REDIS_DATABASE : int = os.getenv("REDIS_DATABASE")
        rd = redis.Redis(host=REDIS_HOST,port=REDIS_PORT,db=REDIS_DATABASE)
        return rd
    except:
        logging.error("Redis connection failure")