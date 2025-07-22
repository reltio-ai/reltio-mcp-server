from dotenv import load_dotenv
load_dotenv()

from src.server import mcp


def run():
    """Run the MCP server with SSE transport."""
    mcp.run(transport="sse")

if __name__ == "__main__":
    run()
