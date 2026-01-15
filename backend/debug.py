#!/usr/bin/env python
"""
Debug script for lead_agent.
Run this file directly in VS Code with breakpoints.

Usage:
    1. Set breakpoints in agent.py or other files
    2. Press F5 or use "Run and Debug" panel
    3. Input messages in the terminal to interact with the agent
"""

import asyncio
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from src.agents import make_lead_agent

load_dotenv()


async def main():
    # Create agent with default config
    config = {
        "configurable": {
            "thread_id": "debug-thread-001",
            "thinking_enabled": True,
            # Uncomment to use a specific model
            "model_name": "doubao-seed-1.8",
        }
    }

    agent = make_lead_agent(config)

    print("=" * 50)
    print("Lead Agent Debug Mode")
    print("Type 'quit' or 'exit' to stop")
    print("=" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                break

            # Invoke the agent
            state = {"messages": [HumanMessage(content=user_input)]}
            result = await agent.ainvoke(state, config=config, context={"thread_id": "debug-thread-001"})

            # Print the response
            if result.get("messages"):
                last_message = result["messages"][-1]
                print(f"\nAgent: {last_message.content}")

        except KeyboardInterrupt:
            print("\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
