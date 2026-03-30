import psutil
from utils.logger import setup_logger

logger = setup_logger("ResourceMonitor")

class ResourceMonitor:
    def get_system_stats(self):
        stats = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent
        }
        logger.info(f"System Stats: {stats}")
        return stats