# Security and validation constants
ENTITY_ID_PATTERN = r'^[a-zA-Z0-9-_/]{5,30}$'  # Example pattern for entity IDs
RELATION_ID_PATTERN = r'^[a-zA-Z0-9-_/]{5,30}$'  # Example pattern for relation IDs
TENANT_ID_PATTERN = r'^[a-zA-Z0-9-_]{3,30}$'  # Example pattern for tenant IDs
MAX_QUERY_LENGTH = 200
MAX_FILTER_LENGTH = 1000
MAX_ENTITY_TYPE_LENGTH = 50
MAX_RESULTS_LIMIT = 100
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
DEFAULT_TIMEOUT = 30  # seconds
LONG_OPERATION_TIMEOUT = 120  # seconds
REQUIRE_TLS = True  # Require HTTPS for all connections
ALLOWED_ORIGINS = ["https://app.reltio.com", "https://api.reltio.com"]  # Allowed origins
HEADER_SOURCE_TAG = "Reltio-Open-MCP-Server"

# Error code definitions
ERROR_CODES = {
    "VALIDATION_ERROR": 400,
    "AUTHENTICATION_ERROR": 401,
    "AUTHORIZATION_ERROR": 403,
    "RESOURCE_NOT_FOUND": 404,
    "TIMEOUT_ERROR": 408,
    "CONFLICT_ERROR": 409,
    "RATE_LIMIT_ERROR": 429,
    "SERVER_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503
}
ACTIVITY_LOG_LABEL="OPEN_MCP_SERVER"