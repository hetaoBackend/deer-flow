from langchain.tools import BaseTool

from src.config import get_app_config
from src.reflection import resolve_variable
from src.tools.builtins import ask_clarification_tool, present_file_tool

BUILTIN_TOOLS = [
    present_file_tool,
    ask_clarification_tool,
]


def get_available_tools(groups: list[str] | None = None) -> list[BaseTool]:
    """Get all available tools from config"""
    config = get_app_config()
    loaded_tools = [resolve_variable(tool.use, BaseTool) for tool in config.tools if groups is None or tool.group in groups]
    return loaded_tools + BUILTIN_TOOLS
