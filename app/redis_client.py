
import json
import os

TESTING = os.getenv("TESTING") == "1"

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def check_login_rate_limit(identifier: str) -> bool:
    """
    Allow at most 5 login attempts per identifier per 60 seconds.
    Returns True if allowed, False if the limit has been reached.
    """
    key = f"login_attempts:{identifier.strip().lower()}"

    try:
        attempts = redis_client.incr(key)

        if attempts == 1:
            redis_client.expire(key, 60)

        return attempts <= 5
    except redis.RedisError:
        raise


def get_cached_balances(group_id: int):
    if TESTING:
        return None

    key = f"group_balances:{group_id}"
    key = f"group_balances:{group_id}"

    try:
        cached = redis_client.get(key)
        if cached is not None:
            return json.loads(cached)
    except (redis.RedisError, json.JSONDecodeError):
        pass

    return None


def cache_balances(group_id: int, balances: dict) -> None:
    if TESTING:
        return

    key = f"group_balances:{group_id}"

    try:
        redis_client.setex(key, 60, json.dumps(balances))
    except redis.RedisError:
        pass


def invalidate_balance_cache(group_id: int) -> None:
    if TESTING:
        return

    key = f"group_balances:{group_id}"

    try:
        redis_client.delete(key)
    except redis.RedisError:
        pass
