"""
Sistema de caché para clasificación de facturas
Mejora performance evitando consultas repetidas a la BD
"""
from typing import Dict, Optional, List, Any
from functools import lru_cache
import hashlib
import json
import time


class CacheManager:
    """Gestor de caché en memoria para clasificación"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Inicializa el gestor de caché
        
        Args:
            ttl_seconds: Tiempo de vida del caché en segundos (default: 1 hora)
        """
        self.ttl = ttl_seconds
        self._cache = {}
        self._timestamps = {}
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Genera clave única para el caché"""
        data = {
            'args': args,
            'kwargs': kwargs
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene valor del caché si existe y no ha expirado"""
        if key not in self._cache:
            return None
        
        # Verificar si ha expirado
        timestamp = self._timestamps.get(key, 0)
        if time.time() - timestamp > self.ttl:
            # Expirado, eliminar
            del self._cache[key]
            del self._timestamps[key]
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any):
        """Guarda valor en el caché"""
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear(self):
        """Limpia todo el caché"""
        self._cache.clear()
        self._timestamps.clear()
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del caché"""
        return {
            'total_entries': len(self._cache),
            'memory_size_kb': len(str(self._cache)) / 1024
        }


# Instancia global del caché
_global_cache = CacheManager(ttl_seconds=3600)


def get_cache() -> CacheManager:
    """Obtiene instancia global del caché"""
    return _global_cache


# Decorador para cachear funciones
def cached(ttl_seconds: int = 3600):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        ttl_seconds: Tiempo de vida del caché
    """
    def decorator(func):
        cache = CacheManager(ttl_seconds=ttl_seconds)
        
        def wrapper(*args, **kwargs):
            # Generar clave
            key = cache._generate_key(*args, **kwargs)
            
            # Intentar obtener del caché
            result = cache.get(key)
            if result is not None:
                return result
            
            # Ejecutar función y guardar en caché
            result = func(*args, **kwargs)
            cache.set(key, result)
            
            return result
        
        wrapper.cache = cache
        wrapper.__wrapped__ = func
        return wrapper
    
    return decorator


class ProveedorCache:
    """Caché específico para proveedores"""
    
    def __init__(self):
        self._cache = {}
        self._nit_to_id = {}
        self._last_update = 0
        self._ttl = 1800  # 30 minutos
    
    def get_by_id(self, proveedor_id: int) -> Optional[Dict]:
        """Obtiene proveedor por ID"""
        if self._is_expired():
            return None
        return self._cache.get(proveedor_id)
    
    def get_by_nit(self, nit: str) -> Optional[Dict]:
        """Obtiene proveedor por NIT"""
        if self._is_expired():
            return None
        
        proveedor_id = self._nit_to_id.get(nit)
        if proveedor_id:
            return self._cache.get(proveedor_id)
        
        return None
    
    def set(self, proveedor: Dict):
        """Guarda proveedor en caché"""
        if 'id' in proveedor:
            self._cache[proveedor['id']] = proveedor
            
            if 'nit' in proveedor:
                self._nit_to_id[proveedor['nit']] = proveedor['id']
            
            self._last_update = time.time()
    
    def set_multiple(self, proveedores: List[Dict]):
        """Guarda múltiples proveedores"""
        for proveedor in proveedores:
            self.set(proveedor)
    
    def _is_expired(self) -> bool:
        """Verifica si el caché ha expirado"""
        return time.time() - self._last_update > self._ttl
    
    def clear(self):
        """Limpia el caché"""
        self._cache.clear()
        self._nit_to_id.clear()
        self._last_update = 0


class UnidadFuncionalCache:
    """Caché específico para unidades funcionales"""
    
    def __init__(self):
        self._cache = {}
        self._by_sucursal = {}
        self._last_update = 0
        self._ttl = 1800  # 30 minutos
    
    def get_by_id(self, unidad_id: int) -> Optional[Dict]:
        """Obtiene unidad por ID"""
        if self._is_expired():
            return None
        return self._cache.get(unidad_id)
    
    def get_by_sucursal(self, sucursal_id: int) -> List[Dict]:
        """Obtiene unidades de una sucursal"""
        if self._is_expired():
            return []
        return self._by_sucursal.get(sucursal_id, [])
    
    def set(self, unidad: Dict):
        """Guarda unidad en caché"""
        if 'id' in unidad:
            self._cache[unidad['id']] = unidad
            
            if 'sucursal_id' in unidad:
                sucursal_id = unidad['sucursal_id']
                if sucursal_id not in self._by_sucursal:
                    self._by_sucursal[sucursal_id] = []
                
                # Evitar duplicados
                if unidad not in self._by_sucursal[sucursal_id]:
                    self._by_sucursal[sucursal_id].append(unidad)
            
            self._last_update = time.time()
    
    def set_multiple(self, unidades: List[Dict]):
        """Guarda múltiples unidades"""
        for unidad in unidades:
            self.set(unidad)
    
    def _is_expired(self) -> bool:
        """Verifica si el caché ha expirado"""
        return time.time() - self._last_update > self._ttl
    
    def clear(self):
        """Limpia el caché"""
        self._cache.clear()
        self._by_sucursal.clear()
        self._last_update = 0


# Instancias globales de cachés especializados
_proveedor_cache = ProveedorCache()
_unidad_cache = UnidadFuncionalCache()


def get_proveedor_cache() -> ProveedorCache:
    """Obtiene caché de proveedores"""
    return _proveedor_cache


def get_unidad_cache() -> UnidadFuncionalCache:
    """Obtiene caché de unidades funcionales"""
    return _unidad_cache


def clear_all_caches():
    """Limpia todos los cachés"""
    _global_cache.clear()
    _proveedor_cache.clear()
    _unidad_cache.clear()
