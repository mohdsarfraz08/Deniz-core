import psutil
import time
from utils.logger import setup_logger

logger = setup_logger("ResourceMonitor")

class ResourceMonitor:
    def __init__(self):
        self.start_time = 0.0

    def get_system_stats(self):
        stats = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent
        }
        logger.info(f"System Stats: {stats}")
        return stats

    def start_intent_tracking(self):
        self.start_time = time.time()
        # Prime the CPU metric (first call returns 0.0 or since last call)
        psutil.cpu_percent(interval=None)

    def stop_intent_tracking(self):
        execution_time = time.time() - self.start_time
        cpu_usage = psutil.cpu_percent(interval=None)
        return {
            "execution_time": execution_time,
            "cpu_usage": cpu_usage
        }