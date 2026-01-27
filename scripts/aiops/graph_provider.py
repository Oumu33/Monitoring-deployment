#!/usr/bin/env python3
"""
Cached Graph Provider for AIOps

Implements a singleton pattern to cache NetworkX graph objects in memory,
drastically reducing database load and improving performance.

Features:
- Singleton pattern (one instance per process)
- TTL-based auto-refresh (default: 5 minutes)
- Thread-safe with read/write locks
- Fallback to stale cache on refresh failure
- Non-blocking updates (serve stale cache while refreshing)
"""

import time
import threading
import logging
import networkx as nx
from typing import Optional
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CachedGraphProvider:
    """
    Singleton provider for cached NetworkX graphs
    
    Maintains an in-memory cache of the topology graph that is refreshed
    periodically from Neo4j. This prevents expensive database queries and
    graph construction operations on every analysis request.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(CachedGraphProvider, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, neo4j_driver: GraphDatabase.Driver, cache_ttl: int = 300):
        """
        Initialize the cached graph provider
        
        Args:
            neo4j_driver: Neo4j database driver
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
        """
        # Prevent re-initialization in singleton
        if not hasattr(self, 'initialized'):
            self.driver = neo4j_driver
            self._cache_ttl = cache_ttl
            self._graph_cache = None
            self._last_update_time = 0
            self._update_lock = threading.Lock()
            self._is_updating = False
            self.initialized = True
            
            logger.info(f"CachedGraphProvider initialized with TTL={cache_ttl}s")
    
    def get_graph(self, force_refresh: bool = False) -> nx.DiGraph:
        """
        Get the cached graph (auto-refresh if expired)
        
        Args:
            force_refresh: Force refresh even if cache is valid
        
        Returns:
            NetworkX DiGraph object
        """
        current_time = time.time()
        
        # Check if cache needs refresh
        needs_refresh = (
            force_refresh or
            self._graph_cache is None or
            current_time - self._last_update_time > self._cache_ttl
        )
        
        if needs_refresh:
            # Try to acquire update lock (non-blocking)
            if self._update_lock.acquire(blocking=False):
                try:
                    self.logger.info("🔄 Cache expired. Refreshing graph from Neo4j...")
                    self._refresh_cache()
                finally:
                    self._update_lock.release()
            else:
                # Another thread is updating, serve stale cache
                self.logger.debug("⚠️ Graph is updating in background. Serving stale cache.")
        
        if self._graph_cache is None:
            # Still no cache? Force synchronous refresh
            self.logger.warning("⚠️ No cache available. Forcing synchronous refresh...")
            with self._update_lock:
                self._refresh_cache()
        
        return self._graph_cache
    
    def _refresh_cache(self):
        """Refresh graph cache from Neo4j"""
        start_time = time.time()
        
        try:
            # Load full topology from database
            new_graph = self._load_full_topology_from_db()
            
            if new_graph is None or new_graph.number_of_nodes() == 0:
                logger.warning("⚠️ Empty graph loaded from database, keeping old cache")
                return
            
            # Atomic swap (Python assignment is atomic)
            old_cache = self._graph_cache
            self._graph_cache = new_graph
            self._last_update_time = time.time()
            
            duration = time.time() - start_time
            old_nodes = old_cache.number_of_nodes() if old_cache else 0
            new_nodes = new_graph.number_of_nodes()
            
            logger.info(
                f"✅ Graph refreshed in {duration:.2f}s. "
                f"Nodes: {old_nodes} → {new_nodes}, "
                f"Edges: {new_graph.number_of_edges()}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh graph: {str(e)}")
            # Keep old cache on failure to prevent service disruption
            import traceback
            logger.debug(traceback.format_exc())
    
    def _load_full_topology_from_db(self) -> nx.DiGraph:
        """
        Load full topology graph from Neo4j
        
        Returns:
            NetworkX DiGraph with nodes and weighted edges
        """
        G = nx.DiGraph()
        
        # Load all nodes
        nodes_query = """
        MATCH (d:Device)
        RETURN d.urn AS urn, d.name AS name, d.ip AS ip, d.type AS type
        """
        
        with self.driver.session() as session:
            result = session.run(nodes_query)
            for record in result:
                urn = record.get('urn') or record.get('name')
                if urn:
                    G.add_node(
                        urn,
                        name=record.get('name'),
                        ip=record.get('ip'),
                        type=record.get('type')
                    )
        
        # Load all edges with weights
        edges_query = """
        MATCH (s:Device)-[r:CONNECTS_TO]->(t:Device)
        RETURN s.urn AS source, t.urn AS target, 
               r.criticality AS criticality, 
               r.source_port AS source_port,
               r.target_port AS target_port
        """
        
        with self.driver.session() as session:
            result = session.run(edges_query)
            for record in result:
                source = record.get('source') or record.get('s')
                target = record.get('target') or record.get('t')
                
                if source and target:
                    criticality = record.get('criticality', 0.5)
                    G.add_edge(
                        source,
                        target,
                        weight=criticality,
                        criticality=criticality,
                        source_port=record.get('source_port'),
                        target_port=record.get('target_port')
                    )
        
        return G
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        cache_age = time.time() - self._last_update_time if self._last_update_time > 0 else 0
        
        stats = {
            'cache_ttl': self._cache_ttl,
            'cache_age': cache_age,
            'cache_age_percent': min(100, (cache_age / self._cache_ttl) * 100),
            'is_expired': cache_age > self._cache_ttl,
            'is_updating': self._is_updating,
            'last_update_time': self._last_update_time
        }
        
        if self._graph_cache:
            stats.update({
                'nodes': self._graph_cache.number_of_nodes(),
                'edges': self._graph_cache.number_of_edges(),
                'is_loaded': True
            })
        else:
            stats.update({
                'nodes': 0,
                'edges': 0,
                'is_loaded': False
            })
        
        return stats
    
    def invalidate_cache(self):
        """Invalidate cache (force refresh on next access)"""
        logger.info("🗑️ Cache invalidated. Will refresh on next access.")
        self._last_update_time = 0
    
    def set_cache_ttl(self, ttl: int):
        """
        Update cache TTL
        
        Args:
            ttl: New TTL in seconds
        """
        self._cache_ttl = ttl
        logger.info(f"Cache TTL updated to {ttl}s")


# Convenience function for getting singleton instance
def get_graph_provider(driver: GraphDatabase.Driver = None, cache_ttl: int = 300) -> CachedGraphProvider:
    """
    Get the singleton GraphProvider instance
    
    Args:
        driver: Neo4j driver (required on first call)
        cache_ttl: Cache TTL in seconds
    
    Returns:
        CachedGraphProvider singleton instance
    """
    if driver is None and CachedGraphProvider._instance is None:
        raise ValueError("Neo4j driver required for first initialization")
    
    return CachedGraphProvider(driver, cache_ttl)