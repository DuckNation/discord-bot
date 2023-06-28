from redis import asyncio as aioredis


class Boosters:
    cache: dict[int, int] = {}
    redis: aioredis.Redis

    def __init__(self, redis: aioredis.ConnectionPool):
        Boosters.redis = redis

    @staticmethod
    async def delete(_id):
        del Boosters.cache[_id]
        await Boosters.redis.hdel("boosters", _id)

    @staticmethod
    async def insert(_id, role_id):
        Boosters.cache[_id] = role_id
        await Boosters.redis.hset("boosters", _id, role_id)

    @staticmethod
    async def load_cache():
        Boosters.cache = await Boosters.redis.hgetall("boosters")
        Boosters.cache = {int(k): int(v) for k, v in Boosters.cache.items()}
