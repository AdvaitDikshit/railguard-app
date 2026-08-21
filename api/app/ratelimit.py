"""Rate limiting via slowapi (Starlette middleware around the `limits` library)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
