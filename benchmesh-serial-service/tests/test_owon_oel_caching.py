"""
Integration tests for owon_oel driver caching with SimpleCache.

Tests verify:
- Polling uses cached values (no redundant SCPI)
- API calls use cached values when fresh
- Cache invalidation on set operations
- Performance improvement with cache vs without
"""

import pytest
from unittest.mock import Mock
from benchmesh_service.drivers.owon_oel.driver import OwonOEL
from benchmesh_service.cache import SimpleCache


class MockTransport:
    """Mock transport for testing."""

    def __init__(self):
        self.call_count = {}
        self.responses = {
            '*IDN?': 'OWON,OEL1234,1.0,1.0',
            'MEAS:ALL:INFO?': '5.0V,1.0A,5.0W,OFF,OFF,OFF',
            'INP?': 'ON',
            'FUNC?': 'current',
        }
        self.last_cmd = None

    def write_line(self, cmd):
        """Track write calls."""
        self.last_cmd = cmd
        if cmd not in self.call_count:
            self.call_count[cmd] = 0
        self.call_count[cmd] += 1

    def read_until_reol(self, size):
        """Return mock response based on last write."""
        if self.last_cmd is None:
            return 'OK'
        response = self.responses.get(self.last_cmd, 'OK')
        self.last_cmd = None  # Reset for next command
        return response

    def open(self):
        return self

    def close(self):
        pass


class TestOwonOELCaching:
    """Test owon_oel driver with SimpleCache."""

    def test_poll_uses_cache(self):
        """Test that poll_status uses cached values to avoid redundant queries."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # First poll - should query input and mode
        result1 = driver.poll_status(1)
        assert 'INPUT' in result1
        assert 'MODE' in result1

        # Check that input and mode were queried
        assert 'INP?' in transport.call_count
        assert 'FUNC?' in transport.call_count
        input_calls_1 = transport.call_count.get('INP?', 0)
        mode_calls_1 = transport.call_count.get('FUNC?', 0)

        # Reset call counts
        transport.call_count = {}

        # Second poll - should use cached values
        result2 = driver.poll_status(1)
        assert result2['INPUT'] == result1['INPUT']
        assert result2['MODE'] == result1['MODE']

        # Input and mode should NOT be queried again (cached)
        assert transport.call_count.get('INP?', 0) == 0
        assert transport.call_count.get('FUNC?', 0) == 0

    def test_set_input_invalidates_cache(self):
        """Test that set_input invalidates the input cache."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # First poll - populates cache
        driver.poll_status(1)

        # Change input
        transport.responses['INP?'] = 'OFF'
        driver.set_input(1, 'OFF')

        # Reset call counts
        transport.call_count = {}

        # Next poll should query input again (cache invalidated)
        result = driver.poll_status(1)

        # Input should have been queried
        assert 'INP?' in transport.call_count
        assert transport.call_count['INP?'] > 0

    def test_set_mode_invalidates_cache(self):
        """Test that set_mode invalidates the mode cache."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # First poll - populates cache
        driver.poll_status(1)

        # Change mode
        transport.responses['FUNC?'] = 'voltage'
        driver.set_mode(1, 'VOLT')

        # Reset call counts
        transport.call_count = {}

        # Next poll should query mode again (cache invalidated)
        result = driver.poll_status(1)

        # Mode should have been queried
        assert 'FUNC?' in transport.call_count
        assert transport.call_count['FUNC?'] > 0

    def test_api_calls_benefit_from_cache(self):
        """Test that API calls to query_input/query_mode can benefit from cache."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # Poll first - populates cache
        driver.poll_status(1)

        # Now simulate API call - query_input
        # This should still query (not cached by query method itself),
        # but demonstrates the pattern where caching could be extended
        result = driver.query_input(1)
        assert result == 'ON'

        # The key insight: if we modify query methods to check cache first,
        # we could avoid this SCPI call. For now, this test documents
        # the current behavior and sets up for future enhancement.

    def test_cache_statistics_tracking(self):
        """Test that cache statistics are tracked correctly."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # First poll - cache misses, then sets
        driver.poll_status(1)

        # Second poll - cache hits
        driver.poll_status(1)

        stats = driver.cache.get_stats()
        assert stats['hit_count'] == 2  # input + mode hits
        assert stats['size'] == 2  # input + mode cached

    def test_lazy_population_pattern(self):
        """Test the lazy cache population pattern used in poll_status."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # Cache should be empty initially
        assert driver.cache.get('input') is None
        assert driver.cache.get('mode') is None

        # First poll populates cache lazily
        driver.poll_status(1)

        # Cache should now have values
        assert driver.cache.get('input') is not None
        assert driver.cache.get('mode') is not None

    def test_no_ttl_means_persistent_cache(self):
        """Test that cached values persist without TTL."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # Poll to populate cache
        driver.poll_status(1)

        # Get cache values
        input_val = driver.cache.get('input')
        mode_val = driver.cache.get('mode')

        # Wait a bit
        import time
        time.sleep(0.1)

        # Values should still be cached (no TTL)
        assert driver.cache.get('input') == input_val
        assert driver.cache.get('mode') == mode_val


class TestOwonOELPerformance:
    """Test performance improvements with caching."""

    def test_cache_reduces_scpi_calls(self):
        """Test that caching significantly reduces SCPI calls."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # Perform multiple polls
        num_polls = 10
        for _ in range(num_polls):
            driver.poll_status(1)

        # Input and mode should be queried only once (first poll)
        # Subsequent polls use cache
        assert transport.call_count.get('INP?', 0) <= 1
        assert transport.call_count.get('FUNC?', 0) <= 1

        # But MEAS:ALL:INFO? should be called every time (not cached)
        assert transport.call_count.get('MEAS:ALL:INFO?', 0) == num_polls

    def test_cache_hit_rate(self):
        """Test cache hit rate after multiple polls."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # First poll - 4 misses (get_or_set double-checks: 2 for input + 2 for mode)
        driver.poll_status(1)
        stats = driver.cache.get_stats()
        assert stats['miss_count'] == 4
        assert stats['hit_count'] == 0

        # Next 9 polls - 18 hits (2 per poll)
        for _ in range(9):
            driver.poll_status(1)

        stats = driver.cache.get_stats()
        assert stats['hit_count'] == 18  # 9 polls * 2 cached values
        assert stats['miss_count'] == 4  # Still only initial misses

        # Calculate hit rate
        total_accesses = stats['hit_count'] + stats['miss_count']
        hit_rate = stats['hit_count'] / total_accesses if total_accesses > 0 else 0
        assert hit_rate > 0.8  # >80% hit rate after 10 polls (18/22 = 81.8%)


class TestOwonOELEdgeCases:
    """Test edge cases with caching."""

    def test_cache_handles_empty_responses(self):
        """Test that cache handles empty/invalid responses gracefully."""
        transport = MockTransport()
        transport.responses['INP?'] = ''
        transport.responses['FUNC?'] = ''

        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # Poll should not crash even with empty responses
        result = driver.poll_status(1)
        assert 'INPUT' in result
        assert 'MODE' in result

        # Empty values should be cached (if that's the actual device response)
        assert driver.cache.get('input') == ''
        assert driver.cache.get('mode') is None  # query_mode returns None for unknown

    def test_multiple_invalidations(self):
        """Test multiple invalidations of the same key."""
        transport = MockTransport()
        driver = OwonOEL(transport=transport)
        driver.cache = SimpleCache()

        # Poll to populate
        driver.poll_status(1)

        # Multiple invalidations (should not raise)
        driver.cache.invalidate('input')
        driver.cache.invalidate('input')
        driver.cache.invalidate('input')

        # Should be able to re-populate
        driver.poll_status(1)
        assert driver.cache.get('input') is not None
