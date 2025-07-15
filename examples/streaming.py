"""
Streaming Integration Test - demonstrates all streaming modes.
"""
import asyncio
from cogency import Agent


async def main():
    """Test streaming modes for cognitive workflow."""
    agent = Agent("streaming_test")
    
    print("🚀 STREAMING INTEGRATION TEST")
    print("=" * 50)
    
    # Stream with trace mode for full visibility
    async for chunk in agent.stream("Tell me about quantum computing", mode="trace"):
        print(chunk, end="", flush=True)
    
    print("\n✅ STREAMING TEST COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())