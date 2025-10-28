"""
Unit tests for SimpleCache utility.

Tests cover:
- Basic get/set operations
- TTL expiry with fractional seconds
- No expiry behavior (ttl=None, ttl=0)
- Thread safety with concurrent access
- Invalidation (single key)
- Clear (bulk invalidation)
- Metrics tracking (hits, misses, evictions)
- Lazy cleanup of expired entries
"""

import pytest
import time
import threading
from benchmesh_service.cache import SimpleCache


class TestSimpleCacheBasics:
    """Test basic cache operations."""

    def test_get_set(self):
        """Test basic get/set operations."""
        cache = SimpleCache()

        # Initially empty
        assert cache.get("key1") is None

        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Set different key
        cache.set("key2", 42)
        assert cache.get("key2") == 42
        assert cache.get("key1") == "value1"  # First key still there

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist returns None."""
        cache = SimpleCache()
        assert cache.get("nonexistent") is None

    def test_set_overwrites_value(self):
        """Test that setting same key overwrites previous value."""
        cache = SimpleCache()
        cache.set("key", "value1")
        cache.set("key", "value2")
        assert cache.get("key") == "value2"

    def test_set_different_types(self):
        """Test storing different value types."""
        cache = SimpleCache()

        cache.set("string", "hello")
        cache.set("int", 123)
        cache.set("float", 3.14)
        cache.set("bool", True)
        cache.set("none", None)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1, "b": 2})

        assert cache.get("string") == "hello"
        assert cache.get("int") == 123
        assert cache.get("float") == 3.14
        assert cache.get("bool") is True
        assert cache.get("none") is None
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1, "b": 2}


class TestCacheTTL:
    """Test TTL (time-to-live) functionality."""

    def test_ttl_expiry(self):
        """Test that values expire after TTL."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0.2)  # 200ms TTL

        # Should be present immediately
        assert cache.get("key") == "value"

        # Wait for expiry
        time.sleep(0.25)

        # Should be expired
        assert cache.get("key") is None

    def test_ttl_fractional_seconds(self):
        """Test TTL with fractional seconds (e.g., 0.6s)."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0.6)  # 600ms TTL

        # Should be present after 400ms
        time.sleep(0.4)
        assert cache.get("key") == "value"

        # Should be expired after 700ms total
        time.sleep(0.35)
        assert cache.get("key") is None

    def test_no_expiry_none(self):
        """Test that ttl=None means no expiry."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=None)

        # Should persist even after significant time
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_no_expiry_zero(self):
        """Test that ttl=0 means no expiry."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0)

        # Should persist even after significant time
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_no_expiry_default(self):
        """Test that omitting ttl means no expiry."""
        cache = SimpleCache()
        cache.set("key", "value")  # No ttl argument

        # Should persist even after significant time
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_ttl_different_per_key(self):
        """Test that different keys can have different TTLs."""
        cache = SimpleCache()
        cache.set("short", "value1", ttl=0.1)  # 100ms
        cache.set("long", "value2", ttl=0.3)   # 300ms
        cache.set("forever", "value3")         # No expiry

        # All present initially
        assert cache.get("short") == "value1"
        assert cache.get("long") == "value2"
        assert cache.get("forever") == "value3"

        # Wait for short to expire
        time.sleep(0.15)
        assert cache.get("short") is None
        assert cache.get("long") == "value2"
        assert cache.get("forever") == "value3"

        # Wait for long to expire
        time.sleep(0.2)
        assert cache.get("short") is None
        assert cache.get("long") is None
        assert cache.get("forever") == "value3"


class TestCacheInvalidation:
    """Test cache invalidation operations."""

    def test_invalidate_single_key(self):
        """Test invalidating a single key."""
        cache = SimpleCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.invalidate("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_invalidate_nonexistent_key(self):
        """Test invalidating a key that doesn't exist (should not raise)."""
        cache = SimpleCache()
        cache.invalidate("nonexistent")  # Should not raise

    def test_clear_all(self):
        """Test clearing all cache entries."""
        cache = SimpleCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_clear_empty_cache(self):
        """Test clearing an empty cache (should not raise)."""
        cache = SimpleCache()
        cache.clear()  # Should not raise


class TestCacheThreadSafety:
    """Test thread safety with concurrent access."""

    def test_concurrent_writes(self):
        """Test concurrent writes from multiple threads."""
        cache = SimpleCache()
        errors = []

        def writer(thread_id, count):
            try:
                for i in range(count):
                    cache.set(f"key_{thread_id}_{i}", f"value_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for tid in range(5):
            t = threading.Thread(target=writer, args=(tid, 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All values should be present
        for tid in range(5):
            for i in range(20):
                key = f"key_{tid}_{i}"
                value = f"value_{tid}_{i}"
                assert cache.get(key) == value

    def test_concurrent_reads_writes(self):
        """Test concurrent reads and writes."""
        cache = SimpleCache()
        cache.set("shared", "initial")
        errors = []
        reads = []

        def reader(count):
            try:
                for _ in range(count):
                    value = cache.get("shared")
                    if value is not None:
                        reads.append(value)
            except Exception as e:
                errors.append(e)

        def writer(count):
            try:
                for i in range(count):
                    cache.set("shared", f"value_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        # Start readers
        for _ in range(3):
            t = threading.Thread(target=reader, args=(50,))
            threads.append(t)
            t.start()

        # Start writers
        for _ in range(2):
            t = threading.Thread(target=writer, args=(50,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # Some reads should have occurred
        assert len(reads) > 0

    def test_concurrent_invalidation(self):
        """Test concurrent invalidation from multiple threads."""
        cache = SimpleCache()

        # Populate cache
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        errors = []

        def invalidator(start, end):
            try:
                for i in range(start, end):
                    cache.invalidate(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for tid in range(5):
            start = tid * 20
            end = start + 20
            t = threading.Thread(target=invalidator, args=(start, end))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All keys should be invalidated
        for i in range(100):
            assert cache.get(f"key_{i}") is None


class TestCacheMetrics:
    """Test cache metrics tracking."""

    def test_hit_count(self):
        """Test that cache hits are tracked."""
        cache = SimpleCache()
        cache.set("key", "value")

        # First access is a hit
        cache.get("key")
        stats = cache.get_stats()
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 0

        # Second access is another hit
        cache.get("key")
        stats = cache.get_stats()
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 0

    def test_miss_count(self):
        """Test that cache misses are tracked."""
        cache = SimpleCache()

        # Access nonexistent key
        cache.get("nonexistent")
        stats = cache.get_stats()
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 1

        # Another miss
        cache.get("another")
        stats = cache.get_stats()
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 2

    def test_eviction_count(self):
        """Test that evictions (expired entries) are tracked."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0.1)

        # Wait for expiry
        time.sleep(0.15)

        # Access triggers lazy cleanup and eviction tracking
        result = cache.get("key")
        assert result is None

        stats = cache.get_stats()
        assert stats["eviction_count"] == 1
        assert stats["miss_count"] == 1  # Expired = miss

    def test_mixed_metrics(self):
        """Test tracking of mixed hits, misses, and evictions."""
        cache = SimpleCache()

        # Set some values
        cache.set("persist", "value1")          # No TTL
        cache.set("expire", "value2", ttl=0.1)  # Short TTL

        # Hits
        cache.get("persist")
        cache.get("expire")

        # Miss
        cache.get("nonexistent")

        # Wait for expiry
        time.sleep(0.15)

        # Eviction (expired key accessed)
        cache.get("expire")

        stats = cache.get_stats()
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 2  # nonexistent + expired
        assert stats["eviction_count"] == 1

    def test_invalidate_updates_eviction_count(self):
        """Test that manual invalidation updates eviction count."""
        cache = SimpleCache()
        cache.set("key", "value")

        cache.invalidate("key")

        stats = cache.get_stats()
        assert stats["eviction_count"] == 1


class TestCacheLazyCleanup:
    """Test lazy cleanup of expired entries."""

    def test_expired_entry_removed_on_access(self):
        """Test that expired entries are removed when accessed."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0.1)

        # Wait for expiry
        time.sleep(0.15)

        # Access should trigger cleanup
        result = cache.get("key")
        assert result is None

        # Entry should be removed from internal storage
        # (We can't directly test internal state, but metrics show eviction)
        stats = cache.get_stats()
        assert stats["eviction_count"] == 1

    def test_multiple_expired_entries_cleaned_individually(self):
        """Test that multiple expired entries are cleaned lazily."""
        cache = SimpleCache()
        cache.set("key1", "value1", ttl=0.1)
        cache.set("key2", "value2", ttl=0.1)
        cache.set("key3", "value3", ttl=0.1)

        # Wait for all to expire
        time.sleep(0.15)

        # Access each, triggering individual cleanup
        cache.get("key1")
        stats = cache.get_stats()
        assert stats["eviction_count"] == 1

        cache.get("key2")
        stats = cache.get_stats()
        assert stats["eviction_count"] == 2

        cache.get("key3")
        stats = cache.get_stats()
        assert stats["eviction_count"] == 3


class TestCacheGetOrSet:
    """Test get_or_set() convenience method."""

    def test_get_or_set_direct_value(self):
        """Test get_or_set with a direct value (non-callable)."""
        cache = SimpleCache()

        # First call - cache miss, stores value
        result = cache.get_or_set("mode", "CURR")
        assert result == "CURR"

        # Second call - cache hit
        result = cache.get_or_set("mode", "VOLT")  # Different value
        assert result == "CURR"  # Returns cached value, not new value

    def test_get_or_set_lambda(self):
        """Test get_or_set with a lambda (no args)."""
        cache = SimpleCache()
        call_count = [0]

        def compute():
            call_count[0] += 1
            return "computed_value"

        # First call - computes
        result = cache.get_or_set("key", lambda: compute())
        assert result == "computed_value"
        assert call_count[0] == 1

        # Second call - cached (doesn't compute)
        result = cache.get_or_set("key", lambda: compute())
        assert result == "computed_value"
        assert call_count[0] == 1  # Not called again

    def test_get_or_set_callable_with_args(self):
        """Test get_or_set with callable and positional args."""
        cache = SimpleCache()
        call_count = [0]

        def compute(x, y):
            call_count[0] += 1
            return x + y

        # First call - computes
        result = cache.get_or_set("sum", compute, 5, 3)
        assert result == 8
        assert call_count[0] == 1

        # Second call - cached
        result = cache.get_or_set("sum", compute, 5, 3)
        assert result == 8
        assert call_count[0] == 1  # Not called again

    def test_get_or_set_callable_with_kwargs(self):
        """Test get_or_set with callable and keyword args."""
        cache = SimpleCache()
        call_count = [0]

        def compute(x, y=0):
            call_count[0] += 1
            return x + y

        # First call - computes
        result = cache.get_or_set("sum", compute, 5, y=3)
        assert result == 8
        assert call_count[0] == 1

        # Second call - cached
        result = cache.get_or_set("sum", compute, 5, y=3)
        assert result == 8
        assert call_count[0] == 1

    def test_get_or_set_with_ttl(self):
        """Test get_or_set with TTL."""
        cache = SimpleCache()
        call_count = [0]

        def compute():
            call_count[0] += 1
            return f"value_{call_count[0]}"

        # First call - computes and caches with TTL
        result = cache.get_or_set("key", compute, ttl=0.1)
        assert result == "value_1"
        assert call_count[0] == 1

        # Second call - cached
        result = cache.get_or_set("key", compute, ttl=0.1)
        assert result == "value_1"
        assert call_count[0] == 1

        # Wait for expiry
        time.sleep(0.15)

        # Third call - expired, computes again
        result = cache.get_or_set("key", compute, ttl=0.1)
        assert result == "value_2"
        assert call_count[0] == 2

    def test_get_or_set_method_reference(self):
        """Test get_or_set with method reference."""
        cache = SimpleCache()

        class MockDriver:
            def __init__(self):
                self.call_count = 0

            def query_mode(self, channel):
                self.call_count += 1
                return f"MODE_{channel}"

        driver = MockDriver()

        # First call - queries
        result = cache.get_or_set("mode", driver.query_mode, 1)
        assert result == "MODE_1"
        assert driver.call_count == 1

        # Second call - cached
        result = cache.get_or_set("mode", driver.query_mode, 1)
        assert result == "MODE_1"
        assert driver.call_count == 1

    def test_get_or_set_with_none_value(self):
        """Test get_or_set with None as direct value."""
        cache = SimpleCache()

        # First call - stores None
        result = cache.get_or_set("key", None)
        assert result is None

        # Second call should NOT be cached (None means miss)
        # This is expected behavior - None is not cached
        call_count = [0]
        def compute():
            call_count[0] += 1
            return "computed"

        result = cache.get_or_set("key", compute)
        assert call_count[0] == 1  # Called because previous None wasn't cached

    def test_get_or_set_variable_value(self):
        """Test get_or_set with variable holding a value."""
        cache = SimpleCache()

        some_value = "pre_computed_value"
        result = cache.get_or_set("key", some_value)
        assert result == "pre_computed_value"

        # Cached
        result = cache.get_or_set("key", "different_value")
        assert result == "pre_computed_value"

    def test_get_or_set_thread_safety(self):
        """Test get_or_set thread safety."""
        cache = SimpleCache()
        call_count = [0]
        lock = threading.Lock()

        def expensive_compute():
            with lock:
                call_count[0] += 1
            time.sleep(0.01)  # Simulate expensive operation
            return "computed"

        # Launch multiple threads trying to get_or_set same key
        threads = []
        results = []

        def worker():
            result = cache.get_or_set("key", expensive_compute)
            results.append(result)

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should get the same result
        assert all(r == "computed" for r in results)

        # Expensive compute should only be called once (or very few times due to race)
        assert call_count[0] <= 2  # Allow for one race condition

    def test_get_or_set_different_keys(self):
        """Test get_or_set with different keys."""
        cache = SimpleCache()

        result1 = cache.get_or_set("key1", "value1")
        result2 = cache.get_or_set("key2", "value2")
        result3 = cache.get_or_set("key1", "value3")  # key1 cached

        assert result1 == "value1"
        assert result2 == "value2"
        assert result3 == "value1"  # Returns cached value

    def test_get_or_set_invalidation(self):
        """Test that invalidation works with get_or_set."""
        cache = SimpleCache()
        call_count = [0]

        def compute():
            call_count[0] += 1
            return f"value_{call_count[0]}"

        # First call
        result = cache.get_or_set("key", compute)
        assert result == "value_1"
        assert call_count[0] == 1

        # Invalidate
        cache.invalidate("key")

        # Next call should recompute
        result = cache.get_or_set("key", compute)
        assert result == "value_2"
        assert call_count[0] == 2

    def test_get_or_set_metrics(self):
        """Test that get_or_set updates metrics correctly."""
        cache = SimpleCache()

        # First call - miss (double-check pattern causes 2 misses), then set
        cache.get_or_set("key", "value")
        stats = cache.get_stats()
        # Note: get_or_set uses double-check locking, so first call = 2 misses
        assert stats["miss_count"] == 2
        assert stats["hit_count"] == 0

        # Second call - hit
        cache.get_or_set("key", "value")
        stats = cache.get_stats()
        assert stats["miss_count"] == 2  # No additional misses
        assert stats["hit_count"] == 1


class TestCacheEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_key(self):
        """Test caching with empty string as key."""
        cache = SimpleCache()
        cache.set("", "value")
        assert cache.get("") == "value"

    def test_zero_ttl_means_no_expiry(self):
        """Test that ttl=0 means no expiry, not instant expiry."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0)
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_negative_ttl_treated_as_no_expiry(self):
        """Test that negative TTL is treated as no expiry."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=-1)
        time.sleep(0.1)
        assert cache.get("key") == "value"

    def test_very_short_ttl(self):
        """Test very short TTL (e.g., 0.01s)."""
        cache = SimpleCache()
        cache.set("key", "value", ttl=0.01)

        # Should expire very quickly
        time.sleep(0.02)
        assert cache.get("key") is None
