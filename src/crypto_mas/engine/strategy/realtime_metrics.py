from collections import defaultdict
from typing import Any


class RealtimeMetricsStore:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.metrics = defaultdict(dict)
        return cls._instance
        
    def set_metric(self, symbol: str, key: str, value: Any):
        self.metrics[symbol][key] = value  # type: ignore
        
    def get_metric(self, symbol: str, key: str, default: Any = None) -> Any:
        return self.metrics[symbol].get(key, default)  # type: ignore
