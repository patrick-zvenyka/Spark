"""
Privacy-preserving rate limiting.

Clients are identified by a salted SHA-256 hash of their IP address that
rotates daily. The hash only lives in the cache for the length of the window
and is never written to the database, so it cannot be used to link a question
back to a student.
"""
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _client_fingerprint(request) -> str:
    ip = request.META.get("REMOTE_ADDR", "")
    if settings.SB_TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
    salt = f"{settings.SECRET_KEY}:{timezone.now().date().isoformat()}"
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


class RateLimiter:
    def __init__(self, scope: str, limit_setting: str, window_setting: str):
        self.scope = scope
        self.limit_setting = limit_setting
        self.window_setting = window_setting

    @property
    def limit(self) -> int:
        return getattr(settings, self.limit_setting)

    @property
    def window(self) -> int:
        return getattr(settings, self.window_setting)

    def _key(self, request) -> str:
        return f"sb:rl:{self.scope}:{_client_fingerprint(request)}"

    def exceeded(self, request) -> bool:
        return cache.get(self._key(request), 0) >= self.limit

    def hit(self, request) -> int:
        key = self._key(request)
        cache.add(key, 0, self.window)
        try:
            return cache.incr(key)
        except ValueError:  # key expired between add and incr
            cache.set(key, 1, self.window)
            return 1


ask_limiter = RateLimiter("ask", "SB_ASK_RATE_LIMIT", "SB_ASK_RATE_WINDOW")
track_limiter = RateLimiter("track", "SB_TRACK_RATE_LIMIT", "SB_TRACK_RATE_WINDOW")
feedback_limiter = RateLimiter("feedback", "SB_FEEDBACK_RATE_LIMIT", "SB_FEEDBACK_RATE_WINDOW")
