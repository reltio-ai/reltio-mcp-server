import os
import base64
RELTIO_SERVER_NAME=os.getenv("RELTIO_SERVER_NAME", "reltio-mcp-server")
RELTIO_ENVIRONMENT=os.getenv("RELTIO_ENVIRONMENT", "dev")
RELTIO_CLIENT_ID=os.getenv("RELTIO_CLIENT_ID", "reltio-client-id")
RELTIO_CLIENT_SECRET=os.getenv("RELTIO_CLIENT_SECRET", "reltio-client-secret")
RELTIO_TENANT=os.getenv("RELTIO_TENANT", "reltio-tenant")
RELTIO_CLIENT_BASIC_TOKEN=base64.b64encode(f"{RELTIO_CLIENT_ID}:{RELTIO_CLIENT_SECRET}".encode()).decode() #base64 encoding of client_id:client_secret
RELTIO_AUTH_SERVER=os.getenv("RELTIO_AUTH_SERVER","https://auth.reltio.com")