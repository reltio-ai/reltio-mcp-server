import json
import requests
import requests
from src.constants import HEADER_SOURCE_TAG
from src.env import RELTIO_CLIENT_BASIC_TOKEN, RELTIO_AUTH_SERVER


from src.env import RELTIO_CLIENT_BASIC_TOKEN, RELTIO_AUTH_SERVER

def get_access_token():
    """Get Reltio access token using environment variables
    Args:
        force_refresh: If True, forces a new token to be retrieved regardless of cache
    """
    # Get token from Reltio
    auth_url = f'{RELTIO_AUTH_SERVER}/oauth/token?grant_type=client_credentials'
    
    headers = {
        "Authorization": f"Basic {RELTIO_CLIENT_BASIC_TOKEN}"
    }
    
    try:
        response = requests.post(auth_url, headers=headers)
        response.raise_for_status()
        result = response.json()
        access_token = result['access_token']
        return access_token
    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message = e.response.text
        raise ValueError(f"Authentication failed: {error_message}")

def get_reltio_headers():
    """Get headers for Reltio API with auth token (using requests version)"""
    token = get_access_token()
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Source': HEADER_SOURCE_TAG
    }
