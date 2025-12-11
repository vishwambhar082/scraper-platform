import random
import time

class SimpleRateLimiter:
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
    def wait(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))
