import asyncio
import logging
from typing import Optional, Dict, Any, Union

import requests
from requests.exceptions import HTTPError

from src.constants import ERROR_CODES, REQUIRE_TLS, ALLOWED_ORIGINS, DEFAULT_TIMEOUT
from src.env import RELTIO_ENVIRONMENT
from src.util.auth import get_reltio_headers
from src.util.exceptions import SecurityError, TimeoutError

# Configure logging
logger = logging.getLogger("mcp.server.reltio")

def get_reltio_url(path: str, partial_path: str, tenant: str):
    """Build a Reltio API URL"""
    return f"https://{RELTIO_ENVIRONMENT}.reltio.com/reltio/{partial_path}/{tenant}/{path}"

def get_reltio_export_job_url(path: str, tenant: str):
    """Build a Reltio Export Job API URL"""
    return f"https://{RELTIO_ENVIRONMENT}.reltio.com/jobs/export/{tenant}/{path}"

def http_request(url: str, 
                 method: str = 'GET', 
                 params: Optional[Dict[str, Union[str, int, float]]] = None, 
                 data: Optional[Any] = None, 
                 headers: Optional[Dict[str, str]] = None,
                 retry_on_401: bool = True
                 ) -> Any:
    """Make an HTTP request and return the JSON response"""
    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=data,
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    
    except HTTPError as e:
        error_message = e.response.text
        if e.response.status_code == 401 and retry_on_401 and "invalid_token" in error_message:
            if headers and 'Authorization' in headers:
                headers = get_reltio_headers()
                return http_request(url, method, params, data, headers, retry_on_401=False)
        raise ValueError(f"API request failed: {e.response.status_code} - {error_message}")

def extract_entity_id(uri: str):
    """Extract entity ID from URI"""
    if not uri:
        return "N/A"
    return uri.split("/")[-1]

def extract_relation_id(uri: str):
    """Extract relation ID from URI"""
    if not uri:
        return "N/A"
    return uri.split("/")[-1]

def extract_name(attributes: dict):
    """Extract name from entity attributes"""
    name_attr = attributes.get("Name", [])
    if name_attr and isinstance(name_attr, list) and len(name_attr) > 0:
        return name_attr[0].get("value", "N/A")
    return "N/A"

def validate_connection_security(url: str, headers: Optional[Dict[str, str]] = None):
    from urllib.parse import urlparse
    parsed_url = urlparse(url)

    if REQUIRE_TLS and parsed_url.scheme != "https":
        raise SecurityError(
            "Insecure connection",
            "TLS is required for all connections"
        )

    if headers and "Origin" in headers:
        origin = headers["Origin"]
        if origin not in ALLOWED_ORIGINS:
            raise SecurityError(
                "Invalid origin",
                f"Origin {origin} is not allowed"
            )

    return True

async def http_request_with_timeout(url: str, 
                                    method: str = 'GET',
                                    params: Optional[Dict[str, Union[str, int, float]]] = None,
                                    data: Optional[Any] = None,
                                    headers: Optional[Dict[str, str]] = None,
                                    timeout: float = DEFAULT_TIMEOUT, 
                                    retry_on_401: bool = True
                                    ) -> Any:
    try:
        validate_connection_security(url, headers)
    except SecurityError as e:
        logger.error(f"Security validation failed: {str(e)}")
        raise

    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: http_request(url, method, params, data, headers, retry_on_401)
            ),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Request timed out after {timeout} seconds: {url}")
        raise TimeoutError(
            "HTTP request",
            timeout,
            {"url": url, "method": method}
        )

def create_error_response(code_key: str, message: str, details: dict = None):
    code = ERROR_CODES.get(code_key, 500)
    safe_details = {}
    if details:
        for key, value in details.items():
            if key in ["field", "resource", "error_type"]:
                safe_details[key] = str(value)

    return {
        "error": {
            "code": code,
            "code_key": code_key,
            "message": message,
            "details": safe_details
        }
    }
