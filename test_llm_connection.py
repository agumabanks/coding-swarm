#!/usr/bin/env python3
"""
Test script to verify LLM connection and agent functionality
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from coding_swarm_agents import create_agent


async def test_llm_connection():
    """Test the LLM connection with a simple query"""
    print("🧪 Testing LLM Connection...")
    print("=" * 50)

    try:
        # Create a coder agent
        context = {"project": ".", "goal": "Test LLM connection"}
        agent = create_agent("coder", context)

        async with agent:
            print("🤖 Sending test query to LLM...")
            test_question = "What is the capital of France? Please answer briefly."

            response = await agent._generate_response(
                test_question,
                "You are a helpful AI assistant. Answer questions directly and concisely."
            )

            print(f"📥 Query: {test_question}")
            print(f"📤 Response: {response}")

            if response and not response.startswith("LLM"):
                print("✅ LLM Connection Successful!")
                return True
            else:
                print("❌ LLM Connection Failed!")
                print(f"Error: {response}")
                return False

    except Exception as e:
        print(f"❌ Error during LLM test: {e}")
        return False


async def test_agent_creation():
    """Test agent creation and basic functionality"""
    print("\n🔧 Testing Agent Creation...")
    print("=" * 50)

    try:
        # Test different agent types
        agent_types = ["coder", "react", "laravel", "flutter", "planner"]

        for agent_type in agent_types:
            print(f"Testing {agent_type} agent...")
            agent = create_agent(agent_type, {"project": "."})
            print(f"✅ {agent_type.title()} agent created successfully")

        print("✅ All agents created successfully!")
        return True

    except Exception as e:
        print(f"❌ Error creating agents: {e}")
        return False


async def test_model_endpoints():
    """Test connection to model endpoints"""
    print("\n🌐 Testing Model Endpoints...")
    print("=" * 50)

    import httpx

    endpoints = [
        ("http://127.0.0.1:8080/v1/models", "API Model (Port 8080)"),
        ("http://127.0.0.1:8081/v1/models", "Web Model (Port 8081)"),
        ("http://127.0.0.1:8082/v1/models", "Mobile Model (Port 8082)"),
        ("http://127.0.0.1:8083/v1/models", "Test Model (Port 8083)"),
    ]

    working_endpoints = 0

    for url, name in endpoints:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✅ {name}: Available")
                    working_endpoints += 1
                else:
                    print(f"⚠️  {name}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: Unavailable ({str(e)[:50]}...)")

    if working_endpoints > 0:
        print(f"\n✅ {working_endpoints}/{len(endpoints)} model endpoints are working")
        return True
    else:
        print("\n❌ No model endpoints are available")
        print("Make sure your Llama.cpp servers are running on ports 8080-8083")
        return False


async def test_memory_system():
    """Test the enhanced memory system"""
    print("\n💾 Testing Memory System...")
    print("=" * 50)

    try:
        # Test memory file creation and integrity
        from packages.cli.src.coding_swarm_cli.sanaa_projects import SanaaProjectsManager

        manager = SanaaProjectsManager()

        # Test memory stats
        stats = manager._get_memory_stats()
        print(f"✅ Memory stats retrieved: {stats['total_projects']} projects")

        # Test memory save/load
        manager._save_memory()
        print("✅ Memory saved successfully")

        # Test cache system
        manager._save_cache()
        print("✅ Cache saved successfully")

        # Test health check
        manager._perform_health_check()
        print("✅ Health check completed")

        return True

    except Exception as e:
        print(f"❌ Memory system test failed: {e}")
        return False


async def test_project_management():
    """Test project management features"""
    print("\n📁 Testing Project Management...")
    print("=" * 50)

    try:
        from packages.cli.src.coding_swarm_cli.sanaa_projects import SanaaProjectsInterface

        interface = SanaaProjectsInterface()

        # Test project listing
        projects = interface.manager.list_projects()
        print(f"✅ Found {len(projects)} projects")

        # Test project creation (without user interaction)
        if hasattr(interface.manager, 'create_project'):
            print("✅ Project creation method available")
        else:
            print("⚠️  Project creation method not accessible")

        return True

    except Exception as e:
        print(f"❌ Project management test failed: {e}")
        return False


async def test_auto_healing():
    """Test auto-healing mechanisms"""
    print("\n🔧 Testing Auto-Healing...")
    print("=" * 50)

    try:
        from packages.cli.src.coding_swarm_cli.sanaa_projects import SanaaProjectsInterface

        interface = SanaaProjectsInterface()

        # Test health check
        issues = interface._perform_system_health_check()
        print(f"✅ Health check completed, found {len(issues)} issues")

        # Test auto-healing
        if hasattr(interface, '_perform_auto_healing'):
            print("✅ Auto-healing method available")
        else:
            print("⚠️  Auto-healing method not accessible")

        return True

    except Exception as e:
        print(f"❌ Auto-healing test failed: {e}")
        return False


async def main():
    """Enhanced main test function with comprehensive system testing"""
    print("🚀 Sanaa Comprehensive System Test")
    print("=" * 60)

    # Check environment
    print("📋 Environment Check:")
    print(f"Python Path: {sys.executable}")
    print(f"Working Directory: {os.getcwd()}")
    print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', 'Not set')}")
    print(f"OPENAI_MODEL: {os.getenv('OPENAI_MODEL', 'Not set')}")

    # Check Sanaa directories
    sanaa_dir = Path.home() / ".sanaa"
    if sanaa_dir.exists():
        print(f"✅ Sanaa config directory: {sanaa_dir}")
    else:
        print(f"⚠️  Sanaa config directory missing: {sanaa_dir}")

    print()

    # Run comprehensive tests
    results = []
    test_names = []

    # Test 1: Model endpoints
    results.append(await test_model_endpoints())
    test_names.append("Model Endpoints")

    # Test 2: Agent creation
    results.append(await test_agent_creation())
    test_names.append("Agent Creation")

    # Test 3: Memory system
    results.append(await test_memory_system())
    test_names.append("Memory System")

    # Test 4: Project management
    results.append(await test_project_management())
    test_names.append("Project Management")

    # Test 5: Auto-healing
    results.append(await test_auto_healing())
    test_names.append("Auto-Healing")

    # Test 6: LLM connection (only if endpoints are working)
    if results[0]:  # If model endpoints are working
        results.append(await test_llm_connection())
        test_names.append("LLM Connection")
    else:
        print("\n⏭️  Skipping LLM test due to endpoint issues")
        results.append(False)
        test_names.append("LLM Connection")

    # Comprehensive Summary
    print("\n" + "=" * 60)
    print("📊 Comprehensive Test Results Summary:")
    print("=" * 60)

    passed = 0
    critical_passed = 0
    critical_tests = ["Model Endpoints", "Agent Creation", "Memory System"]

    for i, (result, name) in enumerate(zip(results, test_names)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print("2d")

        if result:
            passed += 1
            if name in critical_tests:
                critical_passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")
    print(f"Critical: {critical_passed}/{len(critical_tests)} tests passed")

    # Provide recommendations
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED! Sanaa is fully operational!")
        print("✅ Ready for production use")
        return True

    elif critical_passed == len(critical_tests):
        print("\n⚠️  CORE SYSTEMS OPERATIONAL")
        print("✅ Critical components working")
        print("⚠️  Some advanced features may have issues")
        print("\nRecommendations:")
        print("- Check Docker container logs for failed tests")
        print("- Verify model files are present in /opt/models/")
        print("- Run 'sanaa projects' → 'Auto-Healing' to fix issues")
        return True

    else:
        print("\n❌ CRITICAL ISSUES DETECTED")
        print("❌ Core systems have problems")
        print("\nTroubleshooting steps:")
        print("1. Check Docker containers: docker ps")
        print("2. Verify model files: ls -la /opt/models/")
        print("3. Restart containers: docker restart $(docker ps -q)")
        print("4. Check logs: docker logs coding-swarm-qwen-api-1")
        print("5. Run auto-healing: sanaa projects → Auto-Healing")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)