import json
import redis
from config import Config

def get_redis():
    """获取Redis连接，失败返回None（自动降级不崩溃）"""
    try:
        r = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            socket_connect_timeout=2,
            decode_responses=True
        )
        r.ping()
        return r
    except Exception:
        return None

def get_cache(key):
    """读取缓存"""
    r = get_redis()
    if not r:
        return None
    try:
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None

def set_cache(key, value, ttl=None):
    """写入缓存"""
    r = get_redis()
    if not r:
        return
    if ttl is None:
        ttl = Config.CACHE_TTL
    try:
        r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception:
        pass

def delete_cache(key):
    """删除缓存（后台修改数据时调用，保证数据一致）"""
    r = get_redis()
    if not r:
        return
    try:
        r.delete(key)
    except Exception:
        pass