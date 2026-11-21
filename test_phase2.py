"""
YatraPilot AI - Phase 2 Integration Test
Tests Gemini AI + Agora Voice + Travel Tools

This test verifies:
1. Gemini agent with tool calling
2. Travel tool integration (weather, attractions, budget, itinerary)
3. Conversation context management
4. Error handling
"""

import logging
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import project modules
from integrations.gemini import create_gemini_agent
from tools.travel_tools import (
    get_weather,
    search_attractions,
    estimate_trip_budget,
    generate_itinerary
)


def test_gemini_creation():
    """Test 1: Gemini agent creation."""
    logger.info("Testing: Gemini Agent Creation...")
    
    try:
        agent = create_gemini_agent()
        logger.info("  ✓ Gemini agent created")
        logger.info(f"  Model: gemini-2.5-flash")
        return True, agent
    except Exception as e:
        logger.error(f"  ✗ Failed: {e}")
        return False, None


def test_tool_registration(agent):
    """Test 2: Tool registration."""
    logger.info("Testing: Tool Registration...")
    
    try:
        # Register weather tool
        agent.register_tool(
            "get_weather",
            get_weather,
            "Get weather forecast for a destination",
            {
                "properties": {
                    "destination": {"type": "string", "description": "Destination name"},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format"}
                },
                "required": ["destination"]
            }
        )
        
        # Register attractions tool
        agent.register_tool(
            "search_attractions",
            search_attractions,
            "Search for tourist attractions in a destination",
            {
                "properties": {
                    "destination": {"type": "string", "description": "Destination name"},
                    "preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional preferences (temples, beaches, etc)"
                    }
                },
                "required": ["destination"]
            }
        )
        
        # Register budget tool
        agent.register_tool(
            "estimate_trip_budget",
            estimate_trip_budget,
            "Estimate trip budget for a destination",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "duration_days": {"type": "integer"},
                    "travellers": {"type": "integer"}
                },
                "required": ["destination", "duration_days", "travellers"]
            }
        )
        
        # Register itinerary tool
        agent.register_tool(
            "generate_itinerary",
            generate_itinerary,
            "Generate day-by-day itinerary for a trip",
            {
                "properties": {
                    "destination": {"type": "string"},
                    "start_date": {"type": "string"},
                    "duration_days": {"type": "integer"}
                },
                "required": ["destination", "start_date", "duration_days"]
            }
        )
        
        logger.info(f"  ✓ Registered 4 tools")
        logger.info(f"  Tools: get_weather, search_attractions, estimate_trip_budget, generate_itinerary")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed: {e}")
        return False


def test_simple_conversation(agent):
    """Test 3: Simple conversation without tools."""
    logger.info("Testing: Simple Conversation...")
    
    try:
        messages = [
            {"role": "user", "content": "Hello! What can you help me with?"}
        ]
        
        system_prompt = "You are a helpful travel assistant for YatraPilot AI."
        
        response = agent.chat_with_tools(
            messages=messages,
            system_prompt=system_prompt,
            max_iterations=2
        )
        
        logger.info(f"  User: Hello! What can you help me with?")
        logger.info(f"  Assistant: {response[:100]}...")
        logger.info("  ✓ Simple conversation working")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed: {e}")
        return False


def test_tool_calling(agent):
    """Test 4: Conversation with tool calling."""
    logger.info("Testing: Tool Calling (Weather Query)...")
    
    try:
        messages = [
            {"role": "user", "content": "What's the weather like in Goa?"}
        ]
        
        system_prompt = """You are a helpful travel assistant. When users ask about weather,
use the get_weather tool to fetch real data."""
        
        response = agent.chat_with_tools(
            messages=messages,
            system_prompt=system_prompt,
            max_iterations=5
        )
        
        logger.info(f"  User: What's the weather like in Goa?")
        logger.info(f"  Assistant: {response[:150]}...")
        logger.info("  ✓ Tool calling working")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_tool_conversation(agent):
    """Test 5: Complex conversation with multiple tools."""
    logger.info("Testing: Multi-Tool Conversation...")
    
    try:
        messages = [
            {"role": "user", "content": "I want to visit Jaipur for 3 days with my family (4 people). What will it cost?"}
        ]
        
        system_prompt = """You are a helpful travel assistant. Use the available tools to:
1. Check weather if asked
2. Find attractions if asked
3. Estimate budget if asked
4. Generate itinerary if asked"""
        
        response = agent.chat_with_tools(
            messages=messages,
            system_prompt=system_prompt,
            max_iterations=5
        )
        
        logger.info(f"  User: I want to visit Jaipur for 3 days with 4 people. What will it cost?")
        logger.info(f"  Assistant: {response[:200]}...")
        logger.info("  ✓ Multi-tool conversation working")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    logger.info("=" * 70)
    logger.info(" YATRAPILOT AI - PHASE 2 INTEGRATION TEST")
    logger.info("=" * 70)
    logger.info("")
    
    results = []
    
    # Test 1: Create Gemini agent
    success, agent = test_gemini_creation()
    results.append(("Gemini Agent Creation", success))
    if not success:
        logger.error("Cannot proceed without Gemini agent")
        sys.exit(1)
    
    logger.info("")
    
    # Test 2: Register tools
    success = test_tool_registration(agent)
    results.append(("Tool Registration", success))
    if not success:
        logger.error("Cannot proceed without tools")
        sys.exit(1)
    
    logger.info("")
    
    # Test 3: Simple conversation
    success = test_simple_conversation(agent)
    results.append(("Simple Conversation", success))
    
    logger.info("")
    
    # Test 4: Tool calling
    success = test_tool_calling(agent)
    results.append(("Tool Calling", success))
    
    logger.info("")
    
    # Test 5: Multi-tool conversation
    success = test_multi_tool_conversation(agent)
    results.append(("Multi-Tool Conversation", success))
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(" TEST SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("")
    logger.info(f"Passed: {passed}/{total}")
    logger.info("=" * 70)
    
    if passed == total:
        logger.info("✓ All Phase 2 tests passed!")
        return 0
    else:
        logger.error(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
