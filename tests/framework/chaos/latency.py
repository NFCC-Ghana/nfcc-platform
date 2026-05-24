"""Latency injection for timeout testing."""

import time
import threading
from typing import Callable, Any
from functools import wraps


class LatencyInjector:
    """Inject latency into function calls."""
    
    @staticmethod
    def inject(seconds: float = 1.0):
        """Decorator to inject latency."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                time.sleep(seconds)
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def inject_random(min_seconds: float = 0.1, max_seconds: float = 3.0):
        """Inject random latency."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                delay = random.uniform(min_seconds, max_seconds)
                time.sleep(delay)
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def inject_timeout(timeout_seconds: float = 0.5):
        """Simulate timeout by sleeping beyond timeout."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                time.sleep(timeout_seconds + 0.1)
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def simulate_slow_model(api_client, endpoint: str, payload: dict, delay: float = 2.0):
        """Simulate slow model inference."""
        def slow_predict(*args, **kwargs):
            time.sleep(delay)
            return [[50.0]]
        
        import src.api.main as api_module
        original_predict = api_module.model.predict
        api_module.model.predict = slow_predict
        
        try:
            response = api_client.post(endpoint, json=payload)
            return response
        finally:
            api_module.model.predict = original_predict
    
    @staticmethod
    def simulate_hanging_model(api_client, endpoint: str, payload: dict):
        """Simulate hanging model (never returns)."""
        import threading
        import src.api.main as api_module
        
        def hanging_predict(*args, **kwargs):
            # This will never return - simulate timeout
            event = threading.Event()
            event.wait(30)  # Wait 30 seconds
            return [[50.0]]
        
        original_predict = api_module.model.predict
        api_module.model.predict = hanging_predict
        
        try:
            response = api_client.post(endpoint, json=payload, timeout=5)
            return response
        except Exception as e:
            return {"error": "timeout", "detail": str(e)}
        finally:
            api_module.model.predict = original_predict
