#!/usr/bin/env python3
"""
Stress Test: Graph Cache Performance Comparison

Compares performance between cached and non-cached graph loading.

Tests:
1. Single request performance (cached vs uncached)
2. Concurrent request handling (100 concurrent requests)
3. Large scale graph loading (5000 nodes)
"""

import sys
import time
import threading
import logging
import statistics
from datetime import datetime
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GraphCacheStressTest:
    """Stress test suite for graph caching"""
    
    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.test_prefix = f"stress_test_{int(datetime.now().timestamp())}"
        self.results = {}
        
    def close(self):
        """Close database connection"""
        self.driver.close()
        
    def run_all_tests(self):
        """Run all stress tests"""
        logger.info("=" * 60)
        logger.info("Graph Cache Stress Test Suite")
        logger.info("=" * 60)
        
        tests = [
            ("Setup Large Scale Topology", self.setup_large_topology),
            ("Test 1: Single Request Performance", self.test_single_request),
            ("Test 2: Cold Start Performance", self.test_cold_start),
            ("Test 3: Warm Cache Performance", self.test_warm_cache),
            ("Test 4: Concurrent Load Test", self.test_concurrent_requests),
            ("Test 5: Cache Invalidation", self.test_cache_invalidation),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n▶ {test_name}")
                result = test_func()
                if result:
                    passed += 1
                    logger.info(f"✓ {test_name} PASSED")
                else:
                    failed += 1
                    logger.warning(f"⚠ {test_name} SKIPPED")
            except AssertionError as e:
                failed += 1
                logger.error(f"✗ {test_name} FAILED: {e}")
            except Exception as e:
                failed += 1
                logger.error(f"✗ {test_name} ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"Test Results: {passed} passed, {failed} failed")
        logger.info("=" * 60)
        
        # Print performance summary
        self._print_performance_summary()
        
        # Cleanup
        self.cleanup_test_data()
        
        return failed == 0
    
    def setup_large_topology(self) -> bool:
        """Create large scale topology (5000 nodes)"""
        logger.info("Creating large scale topology (5000 nodes)...")
        
        with self.driver.session() as session:
            # Create 5000 devices in batches
            batch_size = 100
            num_devices = 5000
            
            for batch_start in range(0, num_devices, batch_size):
                batch_end = min(batch_start + batch_size, num_devices)
                
                # Create devices
                devices = []
                for i in range(batch_start, batch_end):
                    devices.append({
                        'name': f'{self.test_prefix}_device_{i}',
                        'ip': f'10.1.{i//256}.{i%256}',
                        'type': 'Server'
                    })
                
                # Batch insert
                session.run("""
                    UNWIND $devices AS device
                    MERGE (d:Device {name: device.name})
                    SET d.ip = device.ip, d.type = device.type
                """, {'devices': devices})
                
                if (batch_end) % 500 == 0:
                    logger.info(f"  Created {batch_end} devices...")
            
            # Create edges (create random connections)
            logger.info("Creating edges...")
            num_edges = 10000
            
            for i in range(num_edges):
                source = f'{self.test_prefix}_device_{i % 1000}'
                target = f'{self.test_prefix}_device_{(i + 500) % 1000}'
                criticality = 0.9 if i % 3 == 0 else 0.5
                
                session.run("""
                    MATCH (s:Device {name: $source})
                    MATCH (t:Device {name: $target})
                    MERGE (s)-[r:CONNECTS_TO]->(t)
                    SET r.criticality = $criticality, r.last_seen = datetime()
                """, {
                    'source': source,
                    'target': target,
                    'criticality': criticality
                })
                
                if (i + 1) % 2000 == 0:
                    logger.info(f"  Created {i + 1} edges...")
            
            logger.info(f"✓ Large scale topology created: {num_devices} nodes, {num_edges} edges")
            
        return True
    
    def test_single_request(self) -> bool:
        """Test single request performance"""
        logger.info("Testing single request performance...")
        
        # Test without cache
        from root_cause_analysis import GraphDependencyAnalyzer
        analyzer_no_cache = GraphDependencyAnalyzer(self.driver, use_cache=False)
        
        start_time = time.time()
        graph_no_cache = analyzer_no_cache.load_weighted_graph()
        time_no_cache = (time.time() - start_time) * 1000  # ms
        
        logger.info(f"  Without cache: {time_no_cache:.2f}ms")
        
        # Test with cache (cold start)
        from graph_provider import get_graph_provider
        provider = get_graph_provider(self.driver, cache_ttl=300)
        provider.invalidate_cache()
        
        start_time = time.time()
        graph_cache_cold = provider.get_graph()
        time_cache_cold = (time.time() - start_time) * 1000
        
        logger.info(f"  With cache (cold): {time_cache_cold:.2f}ms")
        
        # Test with cache (warm)
        start_time = time.time()
        graph_cache_warm = provider.get_graph()
        time_cache_warm = (time.time() - start_time) * 1000
        
        logger.info(f"  With cache (warm): {time_cache_warm:.2f}ms")
        
        # Store results
        self.results['single_request'] = {
            'no_cache_ms': time_no_cache,
            'cache_cold_ms': time_cache_cold,
            'cache_warm_ms': time_cache_warm,
            'speedup_cold': time_no_cache / time_cache_cold if time_cache_cold > 0 else 0,
            'speedup_warm': time_no_cache / time_cache_warm if time_cache_warm > 0 else 0
        }
        
        # Assert that cache is faster
        assert time_cache_warm < time_no_cache, "Cache should be faster than DB query"
        assert time_cache_warm < 10, "Cache should be < 10ms"
        
        logger.info(f"  ✓ Speedup (cold): {self.results['single_request']['speedup_cold']:.1f}x")
        logger.info(f"  ✓ Speedup (warm): {self.results['single_request']['speedup_warm']:.1f}x")
        
        return True
    
    def test_cold_start(self) -> bool:
        """Test cold start performance (first request)"""
        logger.info("Testing cold start performance...")
        
        from graph_provider import get_graph_provider
        provider = get_graph_provider(self.driver, cache_ttl=300)
        provider.invalidate_cache()
        
        # First request (cold)
        times = []
        for i in range(3):
            provider.invalidate_cache()
            start_time = time.time()
            graph = provider.get_graph()
            duration = (time.time() - start_time) * 1000
            times.append(duration)
            logger.info(f"  Cold start {i+1}: {duration:.2f}ms")
        
        avg_cold = statistics.mean(times)
        logger.info(f"  Average cold start: {avg_cold:.2f}ms")
        
        self.results['cold_start'] = {
            'avg_ms': avg_cold,
            'min_ms': min(times),
            'max_ms': max(times)
        }
        
        return True
    
    def test_warm_cache(self) -> bool:
        """Test warm cache performance (subsequent requests)"""
        logger.info("Testing warm cache performance...")
        
        from graph_provider import get_graph_provider
        provider = get_graph_provider(self.driver, cache_ttl=300)
        
        # Warm up cache
        provider.get_graph()
        
        # Test 100 requests
        times = []
        for i in range(100):
            start_time = time.time()
            graph = provider.get_graph()
            duration = (time.time() - start_time) * 1000  # ms
            times.append(duration)
        
        avg_warm = statistics.mean(times)
        min_warm = min(times)
        max_warm = max(times)
        p95 = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        logger.info(f"  Average: {avg_warm:.3f}ms")
        logger.info(f"  Min: {min_warm:.3f}ms")
        logger.info(f"  Max: {max_warm:.3f}ms")
        logger.info(f"  P95: {p95:.3f}ms")
        
        self.results['warm_cache'] = {
            'avg_ms': avg_warm,
            'min_ms': min_warm,
            'max_ms': max_warm,
            'p95_ms': p95
        }
        
        # Assert that cache is fast
        assert avg_warm < 5, f"Average cache access should be < 5ms, got {avg_warm:.2f}ms"
        assert p95 < 10, f"P95 cache access should be < 10ms, got {p95:.2f}ms"
        
        return True
    
    def test_concurrent_requests(self) -> bool:
        """Test concurrent request handling"""
        logger.info("Testing concurrent requests (100 concurrent)...")
        
        from graph_provider import get_graph_provider
        provider = get_graph_provider(self.driver, cache_ttl=300)
        
        # Warm up cache
        provider.get_graph()
        
        # Concurrent access test
        num_threads = 100
        results = []
        lock = threading.Lock()
        
        def worker():
            start_time = time.time()
            graph = provider.get_graph()
            duration = (time.time() - start_time) * 1000  # ms
            with lock:
                results.append(duration)
        
        # Start threads
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        total_time = (time.time() - start_time) * 1000
        
        avg_time = statistics.mean(results)
        max_time = max(results)
        p95 = statistics.quantiles(results, n=20)[18] if len(results) >= 20 else max(results)
        
        logger.info(f"  Total time: {total_time:.2f}ms for {num_threads} requests")
        logger.info(f"  Average per request: {avg_time:.3f}ms")
        logger.info(f"  Max per request: {max_time:.3f}ms")
        logger.info(f"  P95: {p95:.3f}ms")
        logger.info(f"  Throughput: {num_threads / (total_time / 1000):.0f} requests/sec")
        
        self.results['concurrent'] = {
            'total_ms': total_time,
            'avg_ms': avg_time,
            'max_ms': max_time,
            'p95_ms': p95,
            'throughput_rps': num_threads / (total_time / 1000)
        }
        
        # Assert concurrent handling works
        assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
        assert avg_time < 10, f"Average should be < 10ms, got {avg_time:.2f}ms"
        
        return True
    
    def test_cache_invalidation(self) -> bool:
        """Test cache invalidation"""
        logger.info("Testing cache invalidation...")
        
        from graph_provider import get_graph_provider
        provider = get_graph_provider(self.driver, cache_ttl=300)
        
        # Get initial cache
        graph1 = provider.get_graph()
        stats1 = provider.get_cache_stats()
        
        logger.info(f"  Before invalidation: nodes={stats1['nodes']}, age={stats1['cache_age']:.0f}s")
        
        # Invalidate cache
        provider.invalidate_cache()
        
        stats2 = provider.get_cache_stats()
        logger.info(f"  After invalidation: age={stats2['cache_age']:.0f}s, expired={stats2['is_expired']}")
        
        assert stats2['is_expired'], "Cache should be expired after invalidation"
        
        # Get new cache (should trigger refresh)
        graph2 = provider.get_graph()
        stats3 = provider.get_cache_stats()
        
        logger.info(f"  After refresh: age={stats3['cache_age']:.0f}s")
        
        assert not stats3['is_expired'], "Cache should be valid after refresh"
        
        logger.info("  ✓ Cache invalidation works correctly")
        
        return True
    
    def _print_performance_summary(self):
        """Print performance summary"""
        logger.info("\n" + "=" * 60)
        logger.info("Performance Summary")
        logger.info("=" * 60)
        
        if 'single_request' in self.results:
            r = self.results['single_request']
            logger.info(f"\nSingle Request Performance:")
            logger.info(f"  Without Cache: {r['no_cache_ms']:.2f}ms")
            logger.info(f"  With Cache (Cold): {r['cache_cold_ms']:.2f}ms")
            logger.info(f"  With Cache (Warm): {r['cache_warm_ms']:.2f}ms")
            logger.info(f"  Speedup (Cold): {r['speedup_cold']:.1f}x")
            logger.info(f"  Speedup (Warm): {r['speedup_warm']:.1f}x")
        
        if 'warm_cache' in self.results:
            r = self.results['warm_cache']
            logger.info(f"\nWarm Cache Performance (100 requests):")
            logger.info(f"  Average: {r['avg_ms']:.3f}ms")
            logger.info(f"  P95: {r['p95_ms']:.3f}ms")
        
        if 'concurrent' in self.results:
            r = self.results['concurrent']
            logger.info(f"\nConcurrent Performance (100 concurrent):")
            logger.info(f"  Total Time: {r['total_ms']:.2f}ms")
            logger.info(f"  Throughput: {r['throughput_rps']:.0f} req/s")
            logger.info(f"  P95: {r['p95_ms']:.3f}ms")
        
        logger.info("\n" + "=" * 60)
        
    def cleanup_test_data(self):
        """Clean up test data"""
        logger.info("\nCleaning up test data...")
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.name STARTS WITH $prefix
                DETACH DELETE n
                RETURN count(n) as count
            """, {'prefix': self.test_prefix})
            
            count = result.single()['count'] if result else 0
            logger.info(f"Cleaned up {count} test nodes")


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stress Test Graph Cache Performance')
    parser.add_argument('--uri', type=str, default='bolt://neo4j:7687', help='Neo4j URI')
    parser.add_argument('--user', type=str, default='neo4j', help='Neo4j username')
    parser.add_argument('--password', type=str, default='password123', help='Neo4j password')
    
    args = parser.parse_args()
    
    # Run tests
    tester = GraphCacheStressTest(args.uri, args.user, args.password)
    success = tester.run_all_tests()
    tester.close()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())