"""
MemU SDK Exceptions

Custom exception classes for MemU SDK operations.
"""


class MemuSDKException(Exception):
    """Base exception for MemU SDK"""

    pass


class MemuAPIException(MemuSDKException):
    """Exception for API-related errors"""

    def __init__(
        self, message: str, status_code: int = None, response_data: dict = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class MemuValidationException(MemuAPIException):
    """Exception for validation errors"""

    pass


class MemuAuthenticationException(MemuAPIException):
    """Exception for authentication errors"""

    pass


class MemuConnectionException(MemuSDKException):
    """Exception for connection errors"""

    pass
