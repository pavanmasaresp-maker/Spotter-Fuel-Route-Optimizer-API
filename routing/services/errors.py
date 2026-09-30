class PlanError(Exception):
    """Error that maps directly to an HTTP status code."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status
