#!/usr/bin/env python3
"""
单例字典管理器 - 提供可监控的全局字典存储
"""

import threading
import time
from typing import Any, Dict, List, Callable, Optional
from utils.logger import logger


class SingletonDictManager:
    """
    单例模式的字典管理器，支持修改监控和日志记录
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._data: Dict[str, Dict] = {}
        self._observers: Dict[str, List[Callable]] = {}
        self._modification_history: List[Dict] = []
        self._dict_lock = threading.RLock()  # 支持递归锁定
        
        logger.info("SingletonDictManager 初始化完成")
    
    def get_dict(self, name: str) -> 'MonitoredDict':
        """
        获取或创建一个被监控的字典
        
        Args:
            name: 字典的名称
            
        Returns:
            MonitoredDict: 被监控的字典对象
        """
        with self._dict_lock:
            if name not in self._data:
                self._data[name] = {}
                self._observers[name] = []
                logger.info(f"创建新的监控字典: {name}")
            
            return MonitoredDict(self, name)
    
    def add_observer(self, dict_name: str, callback: Callable[[str, str, Any, Any], None]):
        """
        为指定字典添加修改观察者
        
        Args:
            dict_name: 字典名称
            callback: 回调函数，签名为 (dict_name, operation, key, value)
        """
        with self._dict_lock:
            if dict_name not in self._observers:
                self._observers[dict_name] = []
            self._observers[dict_name].append(callback)
            logger.info(f"为字典 {dict_name} 添加观察者")
    
    def remove_observer(self, dict_name: str, callback: Callable):
        """
        移除观察者
        """
        with self._dict_lock:
            if dict_name in self._observers and callback in self._observers[dict_name]:
                self._observers[dict_name].remove(callback)
                logger.info(f"从字典 {dict_name} 移除观察者")
    
    def _notify_observers(self, dict_name: str, operation: str, key: Any = None, value: Any = None, old_value: Any = None):
        """
        通知所有观察者字典发生了修改
        """
        timestamp = time.time()
        modification_info = {
            'timestamp': timestamp,
            'dict_name': dict_name,
            'operation': operation,
            'key': key,
            'value': value,
            'old_value': old_value
        }
        
        # 记录修改历史
        self._modification_history.append(modification_info)
        
        # 限制历史记录数量
        if len(self._modification_history) > 1000:
            self._modification_history = self._modification_history[-500:]
        
        # 记录日志
        if operation in ['set', 'update']:
            logger.info(f"字典修改 [{dict_name}]: {operation} key='{key}' value='{value}' (old_value='{old_value}')")
        elif operation == 'delete':
            logger.info(f"字典修改 [{dict_name}]: {operation} key='{key}' (old_value='{old_value}')")
        elif operation == 'clear':
            logger.info(f"字典修改 [{dict_name}]: {operation} (cleared all items)")
        else:
            logger.info(f"字典修改 [{dict_name}]: {operation}")
        
        # 通知观察者
        if dict_name in self._observers:
            for observer in self._observers[dict_name][:]:  # 复制列表避免修改冲突
                try:
                    observer(dict_name, operation, key, value, old_value)
                except Exception as e:
                    logger.error(f"观察者回调失败: {e}")
    
    def get_modification_history(self, dict_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        获取修改历史
        
        Args:
            dict_name: 字典名称，None表示获取所有字典的历史
            limit: 返回记录数量限制
            
        Returns:
            修改历史列表
        """
        with self._dict_lock:
            history = self._modification_history
            if dict_name:
                history = [h for h in history if h['dict_name'] == dict_name]
            return history[-limit:] if limit > 0 else history
    
    def clear_history(self, dict_name: Optional[str] = None):
        """
        清除修改历史
        """
        with self._dict_lock:
            if dict_name:
                self._modification_history = [h for h in self._modification_history if h['dict_name'] != dict_name]
                logger.info(f"清除字典 {dict_name} 的修改历史")
            else:
                self._modification_history.clear()
                logger.info("清除所有字典的修改历史")
    
    def get_all_dict_names(self) -> List[str]:
        """
        获取所有字典名称
        """
        with self._dict_lock:
            return list(self._data.keys())
    
    def get_dict_info(self, dict_name: str) -> Dict:
        """
        获取字典信息
        """
        with self._dict_lock:
            if dict_name not in self._data:
                return {"exists": False}
            
            return {
                "exists": True,
                "size": len(self._data[dict_name]),
                "keys": list(self._data[dict_name].keys()),
                "observers_count": len(self._observers.get(dict_name, []))
            }


class MonitoredDict:
    """
    被监控的字典类，所有操作都会被记录和通知观察者
    """
    
    def __init__(self, manager: SingletonDictManager, name: str):
        self._manager = manager
        self._name = name
    
    @property
    def _data(self):
        return self._manager._data[self._name]
    
    def __getitem__(self, key):
        with self._manager._dict_lock:
            return self._data[key]
    
    def __setitem__(self, key, value):
        with self._manager._dict_lock:
            old_value = self._data.get(key)
            self._data[key] = value
            self._manager._notify_observers(self._name, 'set', key, value, old_value)
    
    def __delitem__(self, key):
        with self._manager._dict_lock:
            old_value = self._data.get(key)
            del self._data[key]
            self._manager._notify_observers(self._name, 'delete', key, None, old_value)
    
    def __contains__(self, key):
        with self._manager._dict_lock:
            return key in self._data
    
    def __len__(self):
        with self._manager._dict_lock:
            return len(self._data)
    
    def __iter__(self):
        with self._manager._dict_lock:
            # 返回键的副本以避免并发修改问题
            return iter(list(self._data.keys()))
    
    def keys(self):
        with self._manager._dict_lock:
            return self._data.keys()
    
    def values(self):
        with self._manager._dict_lock:
            return self._data.values()
    
    def items(self):
        with self._manager._dict_lock:
            return self._data.items()
    
    def get(self, key, default=None):
        with self._manager._dict_lock:
            return self._data.get(key, default)
    
    def pop(self, key, *args):
        with self._manager._dict_lock:
            old_value = self._data.get(key)
            result = self._data.pop(key, *args)
            if key in self._data or len(args) == 0:  # 如果键存在或没有默认值
                self._manager._notify_observers(self._name, 'delete', key, None, old_value)
            return result
    
    def popitem(self):
        with self._manager._dict_lock:
            key, value = self._data.popitem()
            self._manager._notify_observers(self._name, 'delete', key, None, value)
            return key, value
    
    def clear(self):
        with self._manager._dict_lock:
            self._data.clear()
            self._manager._notify_observers(self._name, 'clear')
    
    def update(self, *args, **kwargs):
        with self._manager._dict_lock:
            # 记录更新前的值
            if args:
                if len(args) > 1:
                    raise TypeError(f"update expected at most 1 arguments, got {len(args)}")
                other = args[0]
                if hasattr(other, "items"):
                    for key, value in other.items():
                        old_value = self._data.get(key)
                        self._data[key] = value
                        self._manager._notify_observers(self._name, 'update', key, value, old_value)
                else:
                    for key, value in other:
                        old_value = self._data.get(key)
                        self._data[key] = value
                        self._manager._notify_observers(self._name, 'update', key, value, old_value)
            
            for key, value in kwargs.items():
                old_value = self._data.get(key)
                self._data[key] = value
                self._manager._notify_observers(self._name, 'update', key, value, old_value)
    
    def setdefault(self, key, default=None):
        with self._manager._dict_lock:
            if key not in self._data:
                self._data[key] = default
                self._manager._notify_observers(self._name, 'set', key, default, None)
            return self._data[key]
    
    def copy(self):
        with self._manager._dict_lock:
            return self._data.copy()
    
    def __repr__(self):
        with self._manager._dict_lock:
            return f"MonitoredDict({self._name}): {repr(self._data)}"
    
    def __str__(self):
        return self.__repr__()


# 创建全局单例实例
dict_manager = SingletonDictManager()


# 便捷函数
def get_monitored_dict(name: str) -> MonitoredDict:
    """
    获取被监控的字典实例
    
    Args:
        name: 字典名称
        
    Returns:
        MonitoredDict: 被监控的字典
    """
    return dict_manager.get_dict(name)


def add_dict_observer(dict_name: str, callback: Callable[[str, str, Any, Any], None]):
    """
    为字典添加观察者
    
    Args:
        dict_name: 字典名称
        callback: 回调函数
    """
    dict_manager.add_observer(dict_name, callback)


def get_dict_history(dict_name: str = None, limit: int = 100) -> List[Dict]:
    """
    获取字典修改历史
    
    Args:
        dict_name: 字典名称，None表示所有字典
        limit: 返回记录数量限制
        
    Returns:
        修改历史列表
    """
    return dict_manager.get_modification_history(dict_name, limit)
