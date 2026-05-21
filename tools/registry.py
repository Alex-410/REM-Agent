import asyncio
from typing import Any


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, description: str, parameters: dict, handler):
        self._tools[name] = {
            "definition": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            },
            "handler": handler
        }

    def get_definitions(self) -> list:
        return [t["definition"] for t in self._tools.values()]

    async def execute(self, name: str, args: dict) -> Any:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}

        try:
            handler = tool["handler"]
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: handler(**args))
            return result
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
