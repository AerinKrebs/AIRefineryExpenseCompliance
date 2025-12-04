"""
Simple test script for Image Understanding Agent
Run with: python test_image_agent.py
"""

import asyncio
import json
import os
import sys

# Import only what exists in your agents.py
from agents import image_understanding_agent


# ==================== TEST UTILITIES ====================

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, name):
        self.passed += 1
        print(f"  ✓ PASSED: {name}")
    
    def add_fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ✗ FAILED: {name}")
        print(f"    Reason: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"TEST RESULTS: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print('='*50)
        return self.failed == 0


results = TestResults()


# ==================== UNIT TESTS ====================

async def test_no_image_data():
    """Test agent behavior when no image is provided"""
    test_name = "No image data provided"
    try:
        result = await image_understanding_agent(
            query="Process this receipt",
            env_variable={},  # No image_data
            chat_history=None
        )
        
        parsed = json.loads(result)
        
        # Check that it failed gracefully
        if parsed.get("success") == False:
            results.add_pass(test_name)
        else:
            results.add_fail(test_name, "Should have returned success=False")
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_empty_image_data():
    """Test agent behavior when image data is empty string"""
    test_name = "Empty image data"
    try:
        result = await image_understanding_agent(
            query="Process this receipt",
            env_variable={"image_data": ""},
            chat_history=None
        )
        
        parsed = json.loads(result)
        
        if parsed.get("success") == False:
            results.add_pass(test_name)
        else:
            results.add_fail(test_name, "Should have returned success=False")
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_none_env_variable():
    """Test agent behavior when env_variable is None"""
    test_name = "None env_variable"
    try:
        result = await image_understanding_agent(
            query="Process this receipt",
            env_variable=None,
            chat_history=None
        )
        
        parsed = json.loads(result)
        
        if parsed.get("success") == False:
            results.add_pass(test_name)
        else:
            results.add_fail(test_name, "Should have returned success=False")
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_returns_valid_json():
    """Test that agent always returns valid JSON"""
    test_name = "Returns valid JSON"
    try:
        result = await image_understanding_agent(
            query="Process this receipt",
            env_variable={},
            chat_history=None
        )
        
        # Should not raise JSONDecodeError
        parsed = json.loads(result)
        
        if isinstance(parsed, dict):
            results.add_pass(test_name)
        else:
            results.add_fail(test_name, "Response should be a dict")
    except json.JSONDecodeError as e:
        results.add_fail(test_name, f"Invalid JSON returned: {e}")
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_response_has_success_field():
    """Test that response contains 'success' field"""
    test_name = "Response has 'success' field"
    try:
        result = await image_understanding_agent(
            query="Process this receipt",
            env_variable={},
            chat_history=None
        )
        
        parsed = json.loads(result)
        
        if "success" in parsed:
            results.add_pass(test_name)
        else:
            results.add_fail(test_name, f"Missing 'success' field. Got: {list(parsed.keys())}")
    except Exception as e:
        results.add_fail(test_name, str(e))


# ==================== MAIN ====================

async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*50)
    print(" IMAGE UNDERSTANDING AGENT - UNIT TESTS")
    print("="*50 + "\n")
    
    print("Running tests...\n")
    
    await test_no_image_data()
    await test_empty_image_data()
    await test_none_env_variable()
    await test_returns_valid_json()
    await test_response_has_success_field()
    
    return results.summary()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)