import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from anthropic import Anthropic
from mcp import ClientSession
from mcp.client.sse import sse_client


# Constants
CLAUDE_API_KEY = "<YOUR_CLAUDE_API_KEY>"
SERVER_URL = "<YOUR SERVER URL Example: http://localhost:8000/sse >"
MODEL_NAME="<CLAUDE MODEL NAME>" # Example: "claude-3-5-sonnet-20241022"
MESSAGE_HISTORY_LIMIT = 4  # Preferably an even number


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.anthropic = Anthropic(api_key=CLAUDE_API_KEY)
        self.exit_stack = AsyncExitStack()
        self.messages = []

    async def connect_to_sse_server(self, server_url: str) -> None:
        """Establish an SSE connection to the MCP server and initialize the client session."""
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()

        await self.session.initialize()

        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print("Initialized SSE client...")
        print("Connected tools:", tool_names)

    async def cleanup(self) -> None:
        """Clean up resources and exit contexts properly."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Send a query to Claude, handle any tool invocations, and return the response."""
        self.messages.append({"role": "user", "content": query})

        response = await self.session.list_tools()
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        final_text = []
        tool_results = []

        claude_response = self.anthropic.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            messages=self.messages,
            tools=tools,
        )

        for content in claude_response.content:
            if content.type == "text":
                final_text.append(content.text)

            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                if getattr(content, "text", None):
                    self.messages.append({"role": "assistant", "content": content.text})

                self.messages.append({"role": "user", "content": result.content})

                claude_followup = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=self.messages,
                )

                if claude_followup.content:
                    followup_text = claude_followup.content[0].text
                    final_text.append(followup_text)

        assistant_reply = "\n".join(final_text)

        self.messages.append({"role": "assistant", "content": assistant_reply})
        self.messages = self.messages[-MESSAGE_HISTORY_LIMIT:]

        return assistant_reply

    async def chat_loop(self) -> None:
        """Run an interactive REPL for chatting with Claude."""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as err:
                print(f"\nError: {str(err)}")


async def main():
    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=SERVER_URL)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
