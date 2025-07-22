import logging

# Configure logging
logger = logging.getLogger("mcp.server.reltio")

class ReltioApiError(Exception):
    """Base exception for Reltio API errors"""
    def __init__(self, code, message, details=None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")

class ValidationError(ReltioApiError):
    """Exception for input validation errors"""
    def __init__(self, message, field=None, details=None):
        super().__init__(400, message, details)
        self.field = field

class AuthenticationError(ReltioApiError):
    """Exception for authentication errors"""
    def __init__(self, message, details=None):
        super().__init__(401, message, details)

class AuthorizationError(ReltioApiError):
    """Exception for authorization errors"""
    def __init__(self, message, details=None):
        super().__init__(403, message, details)

class ResourceNotFoundError(ReltioApiError):
    """Exception for resource not found errors"""
    def __init__(self, resource_type, resource_id, details=None):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(404, message, details)

class SecurityError(ReltioApiError):
    """Exception for security-related errors"""
    def __init__(self, message, details=None):
        # Don't include sensitive details in the message
        safe_message = "Security requirements not met"
        # Log the actual issue securely
        logger.error(f"Security error: {message}", extra={"details": details})
        super().__init__(403, safe_message, None)

class TimeoutError(ReltioApiError):
    """Exception for timeout errors"""
    def __init__(self, operation, timeout, details=None):
        message = f"Operation {operation} timed out after {timeout} seconds"
        super().__init__(408, message, details)