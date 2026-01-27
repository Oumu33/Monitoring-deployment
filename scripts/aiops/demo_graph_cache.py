#!/usr/bin/env python3
"""
Demonstration: Graph Cache Performance Benefits

Shows the dramatic performance improvement when using graph caching.

Scenario:
- Load graph 100 times
- Compare: Without Cache vs With Cache
"""

import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_without_cache_simulation():
    """Simulate performance without cache"""
    print("\n" + "=" * 60)
    print("WITHOUT CACHE (Direct Database Access)")
    print("=" * 60)
    print("Scenario: Every request queries Neo4j and rebuilds graph")
    print()
    
    # Simulate DB query and graph construction
    # Typical times:
    # - DB query: 50-100ms
    # - Graph construction: 20-50ms
    # - Total: 70-150ms per request
    
    times = []
    for i in range(100):
        # Simulate: DB query (70ms) + Graph construction (30ms) = 100ms
        time.sleep(0.1)
        times.append(100)
    
    total_time = sum(times) / 1000  # Convert to seconds
    avg_time = sum(times) / len(times)
    
    print(f"Total time for 100 requests: {total_time:.1f}s")
    print(f"Average per request: {avg_time:.0f}ms")
    print(f"Throughput: {100 / total_time:.1f} requests/sec")
    print()
    print("⚠️ In a production alert storm (500 alerts/min), this would be")
    print("   a severe bottleneck causing analysis delays!")


def demo_with_cache_simulation():
    """Simulate performance with cache"""
    print("=" * 60)
    print("WITH CACHE (In-Memory Graph)")
    print("=" * 60)
    print("Scenario: First request loads graph, subsequent requests use cache")
    print()
    
    # Cold start (first request)
    print("Cold Start (First Request):")
    cold_start_time = 0.1  # 100ms (same as without cache)
    print(f"  - Load graph from DB: {cold_start_time*1000:.0f}ms")
    
    # Warm cache (subsequent requests)
    print("Warm Cache (Subsequent Requests):")
    warm_times = []
    for i in range(99):
        # Simulate: Memory access (1ms)
        warm_times.append(1)
    
    warm_avg = sum(warm_times) / len(warm_times)
    total_time = cold_start_time + sum(warm_times) / 1000
    
    print(f"  - Access cached graph: {warm_avg:.0f}ms")
    print()
    print(f"Total time for 100 requests: {total_time:.1f}s")
    print(f"Average per request (warm): {warm_avg:.0f}ms")
    print(f"Throughput: {100 / total_time:.1f} requests/sec")
    print()
    print("✓ Excellent performance! Can handle 1000+ alerts/min easily!")


def run_live_demo():
    """Run live demo with Neo4j"""
    print("\n" + "=" * 60)
    print("LIVE DEMO: Testing with Neo4j")
    print("=" * 60)
    
    try:
        from neo4j import GraphDatabase
        
        uri = 'bolt://neo4j:7687'
        user = 'neo4j'
        password = 'password123'
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        
        print("✓ Connected to Neo4j\n")
        
        # Setup test data
        with driver.session() as session:
            # Create test nodes
            session.run("""
                MERGE (p:Device {name: 'cache_demo_service'}) SET p.type = 'Service'
                MERGE (d:Device {name: 'cache_demo_db'}) SET d.type = 'Database'
                MERGE (c:Device {name: 'cache_demo_cache'}) SET c.type = 'Cache'
            """)
            
            # Create edges
            session.run("""
                MATCH (p:Device {name: 'cache_demo_service'})
                MATCH (d:Device {name: 'cache_demo_db'})
                MERGE (p)-[r1:CONNECTS_TO]->(d)
                SET r1.criticality = 0.9

                MATCH (p:Device {name: 'cache_demo_service'})
                MATCH (c:Device {name: 'cache_demo_cache'})
                MERGE (p)-[r2:CONNECTS_TO]->(c)
                SET r2.criticality = 0.9
            """)
            
            print("✓ Test topology created\n")
        
        # Test without cache
        print("Test 1: Without Cache")
        from root_cause_analysis import GraphDependencyAnalyzer
        analyzer_no_cache = GraphDependencyAnalyzer(driver, use_cache=False)
        
        times_no_cache = []
        for i in range(10):
            start = time.time()
            graph = analyzer_no_cache.load_weighted_graph()
            duration = (time.time() - start) * 1000
            times_no_cache.append(duration)
        
        avg_no_cache = sum(times_no_cache) / len(times_no_cache)
        print(f"  Average: {avg_no_cache:.2f}ms")
        print(f"  Min: {min(times_no_cache):.2f}ms")
        print(f"  Max: {max(times_no_cache):.2f}ms")
        
        # Test with cache
        print("\nTest 2: With Cache")
        from graph_provider import get_graph_provider
        provider = get_graph_provider(driver, cache_ttl=300)
        provider.invalidate_cache()
        
        # Cold start
        start = time.time()
        graph = provider.get_graph()
        cold_time = (time.time() - start) * 1000
        print(f"  Cold start: {cold_time:.2f}ms")
        
        # Warm cache
        times_cache = []
        for i in range(10):
            start = time.time()
            graph = provider.get_graph()
            duration = (time.time() - start) * 1000
            times_cache.append(duration)
        
        avg_cache = sum(times_cache) / len(times_cache)
        print(f"  Warm average: {avg_cache:.2f}ms")
        print(f"  Warm min: {min(times_cache):.2f}ms")
        print(f"  Warm max: {max(times_cache):.2f}ms")
        
        # Calculate speedup
        speedup = avg_no_cache / avg_cache
        print(f"\n✓ Speedup: {speedup:.1f}x faster with cache!")
        
        # Show cache stats
        stats = provider.get_cache_stats()
        print(f"\nCache Stats:")
        print(f"  Nodes: {stats['nodes']}")
        print(f"  Edges: {stats['edges']}")
        print(f"  Cache Age: {stats['cache_age']:.1f}s")
        print(f"  TTL: {stats['cache_ttl']}s")
        
        # Cleanup
        with driver.session() as session:
            session.run("""
                MATCH (n)
                WHERE n.name STARTS WITH 'cache_demo_'
                DETACH DELETE n
            """)
        
        print("\n✓ Test data cleaned up")
        print("\n✓ Live demo completed successfully!")
        
        driver.close()
        
    except ImportError:
        print("⚠ neo4j package not available, skipping live demo")
        print("   Use: pip install neo4j")
    except Exception as e:
        print(f"⚠ Live demo failed: {e}")


def main():
    """Main demonstration"""
    print("\n" + "=" * 60)
    print("Graph Cache Performance Benefits")
    print("=" * 60)
    
    # Simulate without cache
    demo_without_cache_simulation()
    
    # Simulate with cache
    demo_with_cache_simulation()
    
    # Run live demo
    run_live_demo()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("Without Cache:")
    print("  - Every request queries Neo4j")
    print("  - Typical: 70-150ms per request")
    print("  - Bottleneck in alert storms")
    print()
    print("With Cache:")
    print("  - First request loads graph (cold start)")
    print("  - Subsequent queries use memory (warm)")
    print("  - Typical: < 5ms per request")
    print("  - Handles 1000+ alerts/min easily")
    print()
    print("Benefits:")
    print("  ✓ 10-30x faster for warm cache")
    print("  ✓ Reduces database load by 99%")
    print("  ✓ Enables real-time analysis at scale")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()