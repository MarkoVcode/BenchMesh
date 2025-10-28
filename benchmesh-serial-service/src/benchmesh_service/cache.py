"""
Universal caching layer for driver values.

Provides thread-safe caching with TTL support to minimize redundant SCPI calls
between polling loops and API requests.
"""

import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple


class SimpleCache:
    """
    Thread-safe cache with TTL support for driver values.

    Features:
    - Thread-safe with internal RLock
    - TTL support with fractional seconds (e.g., 0.6s)
    - No expiry when ttl=None or ttl=0
    - Lazy expiry (cleanup on access)
    - Metrics tracking (hits, misses, evictions)

    Usage:
        cache = SimpleCache()

        # Manual get/set
        cache.set("voltage", 5.0, ttl=1.0)  # Cache for 1 second
        value = cache.get("voltage")         # Returns 5.0 if not expired, None if expired

        # Automatic get-or-compute (recommended)
        value = cache.get_or_set("mode", self.query_mode, 1)  # Get from cache or query

        # Other operations
        cache.invalidate("voltage")          # Remove from cache
        cache.clear()                        # Remove all entries
        stats = cache.get_stats()            # Get metrics
    """

    def __init__(self, default_ttl: Optional[float] = None):
        """
        Initialize cache.

        Args:
            default_ttl: Default TTL in seconds (None = no expiry by default)
        """
        # Cache storage: key -> (value, expiry_time)
        # expiry_time is None for no expiry, or timestamp for TTL
        self._cache: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl

        # Metrics
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if present and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._miss_count += 1
                return None

            value, expiry_time = self._cache[key]

            # Check expiry
            if expiry_time is not None and time.time() > expiry_time:
                # Expired - remove and count as eviction
                del self._cache[key]
                self._eviction_count += 1
                self._miss_count += 1
                return None

            # Cache hit
            self._hit_count += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None or 0 = no expiry, fractional values supported)
        """
        with self._lock:
            # Determine TTL to use
            effective_ttl = ttl if ttl is not None else self._default_ttl

            # Calculate expiry time
            if effective_ttl is None or effective_ttl <= 0:
                # No expiry
                expiry_time = None
            else:
                # Set expiry timestamp
                expiry_time = time.time() + effective_ttl

            self._cache[key] = (value, expiry_time)

    def get_or_set(
        self,
        key: str,
        value_or_callable,
        *args,
        ttl: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Get from cache or compute/store if missing.

        Supports both direct values and callables (functions/methods) for maximum flexibility.

        Args:
            key: Cache key
            value_or_callable: Either a direct value OR a callable to invoke
            *args: Arguments to pass to callable (ignored if not callable)
            ttl: Time-to-live in seconds (None or 0 = no expiry)
            **kwargs: Keyword arguments to pass to callable (ignored if not callable)

        Returns:
            Cached or computed value

        Examples:
            # Direct value (no computation)
            mode = cache.get_or_set("mode", "CURR")

            # Callable with no args (lambda)
            mode = cache.get_or_set("mode", lambda: self.query_mode(1))

            # Callable with args (no lambda needed)
            mode = cache.get_or_set("mode", self.query_mode, 1)

            # Callable with TTL
            voltage = cache.get_or_set("voltage", self.query_voltage, 1, ttl=0.5)

            # Variable holding a value
            cached_val = cache.get_or_set("result", some_computed_value)
        """
        # Check cache first
        cached = self.get(key)
        if cached is not None:
            return cached

        # Cache miss - compute or use direct value
        with self._lock:
            # Double-check after acquiring lock (another thread may have set it)
            cached = self.get(key)
            if cached is not None:
                return cached

            # Check if it's callable
            if callable(value_or_callable):
                # Invoke the callable with args/kwargs
                if args or kwargs:
                    cached = value_or_callable(*args, **kwargs)
                else:
                    cached = value_or_callable()
            else:
                # Use the value directly
                cached = value_or_callable

            # Store in cache
            self.set(key, cached, ttl=ttl)
            return cached

    def invalidate(self, key: str) -> None:
        """
        Remove a specific key from cache.

        Args:
            key: Cache key to remove
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._eviction_count += 1

    def clear(self) -> None:
        """Remove all entries from cache."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit_count, miss_count, eviction_count, size
        """
        with self._lock:
            return {
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "eviction_count": self._eviction_count,
                "size": len(self._cache),
            }

    def reset_stats(self) -> None:
        """Reset all statistics counters to zero."""
        with self._lock:
            self._hit_count = 0
            self._miss_count = 0
            self._eviction_count = 0
