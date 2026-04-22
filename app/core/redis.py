import redis
from .config import settings

def get_redis_client() -> redis.Redis:
    """
    Returns a Redis client from the connection pool.
    """
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
