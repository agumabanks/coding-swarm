#!/usr/bin/env python3
"""Test script to check if imports work correctly"""

import sys
from pathlib import Path

# Add the project root to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    # Test core imports
    from coding_swarm_core.projects import ProjectRegistry, Project, FileIndexEntry
    print("✓ Core imports successful")

    # Test CLI imports
    from coding_swarm_cli.interactive import app
    print("✓ CLI imports successful")

    # Test API imports
    from api.providers import BaseProvider, get_provider
    print("✓ API imports successful")

    print("\n🎉 All imports successful! The circular import issue has been resolved.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Other error: {e}")
    sys.exit(1)