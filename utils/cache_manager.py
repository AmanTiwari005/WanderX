"""
Lightweight in-memory cache for API responses.
Reduces redundant API calls and improves performance.
"""

import time
from typing import Any, Optional
from datetime import datetime, timedelta


class CacheManager:
    def __init__(self):
        self._cache = {}
        self._ttls = {
            "weather": 1800,      # 30 minutes
            "geocode": 86400,     # 24 hours  
            "crowd": 900,         # 15 minutes
            "news": 3600,         # 1 hour
            "places": 3600,       # 1 hour
        }
    
    def _get_key(self, cache_type: str, identifier: str) -> str:
        """Generate cache key"""
        return f"{cache_type}:{identifier}"
    
    def get(self, cache_type: str, identifier: str) -> Optional[Any]:
        """
        Retrieve cached data if valid.
        
        Args:
            cache_type: Type of cache (weather, geocode, crowd, etc.)
            identifier: Unique identifier (location name, coordinates, etc.)
            
        Returns:
            Cached data if valid, None otherwise
        """
        key = self._get_key(cache_type, identifier)
        
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        ttl = self._ttls.get(cache_type, 1800)
        
        # Check if expired
        if time.time() - entry["timestamp"] > ttl:
            del self._cache[key]
            return None
        
        return entry["data"]
    
    def set(self, cache_type: str, identifier: str, data: Any):
        """
        Store data in cache.
        
        Args:
            cache_type: Type of cache
            identifier: Unique identifier
            data: Data to cache
        """
        key = self._get_key(cache_type, identifier)
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
    
    def clear(self, cache_type: Optional[str] = None):
        """
        Clear cache.
        
        Args:
            cache_type: Specific cache type to clear, or None to clear all
        """
        if cache_type is None:
            self._cache.clear()
        else:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{cache_type}:")]
            for key in keys_to_delete:
                del self._cache[key]
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        stats = {
            "total_entries": len(self._cache),
            "by_type": {}
        }
        
        for key in self._cache.keys():
            cache_type = key.split(":")[0]
            stats["by_type"][cache_type] = stats["by_type"].get(cache_type, 0) + 1
        
        return stats


# Global cache instance
_global_cache = None

def get_cache() -> CacheManager:
    """Get or create global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache
