class BaseController:
    """
    Base class for all automation controllers.
    Holds a reference to the backend.
    """

    def __init__(self, backend) -> None:
        self.backend = backend
