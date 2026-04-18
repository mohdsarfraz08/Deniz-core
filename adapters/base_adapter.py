from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def execute_command(self, command: str):
        pass

    @abstractmethod
    def get_status(self):
        pass

    @abstractmethod
    def open_app(self, app_name: str):
        pass

    @abstractmethod
    def close_app(self, app_name: str):
        pass

    @abstractmethod
    def get_time(self):
        pass

    @abstractmethod
    def get_cpu_usage(self):
        pass

    @abstractmethod
    def get_memory_usage(self):
        pass