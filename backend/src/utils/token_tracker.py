import threading
import time
from typing import Dict, Any

class TokenTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TokenTracker, cls).__new__(cls)
                    cls._instance.reset()
        return cls._instance

    def reset(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.requests = 0
        self.cost_estimate = 0.0
        # Approximate costs per 1k tokens (example rates, adjust as needed)
        self.rates = {
            "input": 0.0005,  # $0.50 per 1M tokens
            "output": 0.0015  # $1.50 per 1M tokens
        }

    def track_usage(self, usage_data: Dict[str, Any]):
        if not usage_data:
            return

        p_tokens = usage_data.get("prompt_tokens", 0)
        c_tokens = usage_data.get("completion_tokens", 0)
        total = usage_data.get("total_tokens", 0)

        with self._lock:
            self.prompt_tokens += p_tokens
            self.completion_tokens += c_tokens
            self.total_tokens += total
            self.requests += 1
            
            # Calculate cost
            cost = (p_tokens / 1000 * self.rates["input"]) + (c_tokens / 1000 * self.rates["output"])
            self.cost_estimate += cost

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_tokens": self.total_tokens,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "requests": self.requests,
                "cost_estimate": round(self.cost_estimate, 6)
            }

token_tracker = TokenTracker()
