"""Atomic leaky bucket admission control, shared by every API worker."""

import hashlib
import hmac
import ipaddress
import math
from functools import lru_cache

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

# Redis TIME avoids clock skew between application workers. Rejected requests do not
# add water. TTL removes idle buckets only after all accepted water has drained.
LEAKY_BUCKET = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local state = redis.call('HMGET', KEYS[1], 'level', 'updated')
local level = tonumber(state[1]) or 0
local updated = tonumber(state[2]) or now
level = math.max(0, level - math.max(0, now - updated) * rate)
local wait = 0
if level + 1 > capacity then
    wait = math.ceil((level + 1 - capacity) / rate)
else
    level = level + 1
end
redis.call('HSET', KEYS[1], 'level', level, 'updated', now)
redis.call('EXPIRE', KEYS[1], math.max(1, math.ceil(level / rate)))
return wait
"""


class LeakyBucket:
    def __init__(self, redis):
        self.redis = redis

    def consume(self, key: str, capacity: int, period: int) -> int:
        if capacity <= 0 or period <= 0:
            raise ValueError("Bucket capacity and period must be positive")
        return int(self.redis.eval(LEAKY_BUCKET, 1, key, capacity, capacity / period))


@lru_cache
def get_limiter():
    return LeakyBucket(
        Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2)
    )


def enforce(request: Request, scope: str, identity: str, capacity: int, period: int):
    settings = get_settings()
    key = hmac.new(settings.auth_secret.encode(), identity.encode(), hashlib.sha256).hexdigest()
    try:
        wait = request.app.state.limiter.consume(f"limit:{scope}:{key}", capacity, period)
    except RedisError:
        raise HTTPException(
            503, "Authentication temporarily unavailable", headers={"Retry-After": "5"}
        )
    if wait:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(math.ceil(wait))})


def auth_ip_limit(request: Request):
    peer = request.client.host if request.client else "unknown"
    try:
        trusted = any(
            ipaddress.ip_address(peer) in ipaddress.ip_network(cidr)
            for cidr in get_settings().trusted_proxy_cidrs
        )
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.headers.get("x-real-ip", "")
        try:
            peer = str(ipaddress.ip_address(forwarded))
        except ValueError:
            raise HTTPException(400, "Invalid client address")
    enforce(request, "auth-ip", peer, 60, 60)
