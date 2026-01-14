"""
Quick Test Runner - For debugging individual test cases
Runs a single test and displays detailed output
"""

import os
import sys
import asyncio
import json
import base64
from pathlib import Path

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import image_understanding_agent, validation_agent

# Update paths
TEST_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VAtesting")


async def quick_test(image_number: int, test_images_dir: str = None):
    """
    Quick test of a single image through the agent pipeline
    
    Args:
        image_number: The test case number (1-50)
        test_images_dir: Directory containing test images
    """
    
    if test_images_dir is None:
        test_images_dir = TEST_IMAGES_DIR
    
    print(f"\n{'='*80}")
    print(f"QUICK TEST - Image #{image_number}")
    print(f"{'='*80}\n")
    
    # Find image file 
    # fixed for being "greedy" 
    test_dir = Path(test_images_dir)
    patterns = [
        f"{image_number} *.png"
    ]
    
    image_path = None
    for pattern in patterns:
        matches = list(test_dir.glob(pattern))
        if matches:
            image_path = str(matches[0])
            break
    
    if not image_path:
        print(f"❌ ERROR: Could not find image for test case #{image_number}")
        print(f"   Searched in: {test_images_dir}/")
        return
    
    print(f"✓ Found image: {image_path}\n")
    
    # Load and encode image
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ ERROR: Could not read image file: {e}")
        return
    
    # Prepare environment
    env_vars = {
        "image_data": image_data,
        "image_type": "receipt",
        "user_id": "quick_test"
    }
    
    # Step 1: Image Understanding Agent
    print("="*80)
    print("STEP 1: IMAGE UNDERSTANDING AGENT")
    print("="*80)
    
    try:
        query = f"Extract all expense data from this receipt image. Test case #{image_number}."
        
        print(f"Running agent...")
        image_result = await image_understanding_agent(
            query=query,
            env_variable=env_vars,
            chat_history=None
        )
        
        image_result_dict = json.loads(image_result)
        
        print("\n📊 IMAGE UNDERSTANDING RESULTS:\n")
        print(json.dumps(image_result_dict, indent=2))
        
        if not image_result_dict.get("success"):
            print("\n❌ Image understanding failed!")
            print(f"Error: {image_result_dict.get('error', 'Unknown')}")
            return
        
        extracted_data = image_result_dict.get("extracted_data", {})
        
        # Display key extracted fields
        print("\n📋 KEY EXTRACTED FIELDS:")
        print(f"  Vendor: {extracted_data.get('vendor_name', 'N/A')}")
        print(f"  Date: {extracted_data.get('date', 'N/A')}")
        print(f"  Total: {extracted_data.get('currency', '')} {extracted_data.get('total_amount', 'N/A')}")
        print(f"  Category: {extracted_data.get('expense_category', 'N/A')}")
        print(f"  Confidence: {extracted_data.get('confidence_score', 'N/A')}")
        
        if extracted_data.get('notes'):
            print(f"  Notes: {extracted_data.get('notes')}")
        
    except Exception as e:
        print(f"\n❌ ERROR in image understanding: {e}")
        return
    
    # Step 2: Validation Agent
    print("\n" + "="*80)
    print("STEP 2: VALIDATION AGENT")
    print("="*80)
    
    try:
        env_vars["extracted_data"] = extracted_data
        
        query = f"Validate this extracted expense data for test case #{image_number}."
        
        print(f"Running agent...")
        validation_result = await validation_agent(
            query=query,
            env_variable=env_vars,
            chat_history=None
        )
        
        validation_result_dict = json.loads(validation_result)
        
        print("\n📊 VALIDATION RESULTS:\n")
        print(json.dumps(validation_result_dict, indent=2))
        
        # Display key validation findings
        print("\n🔍 VALIDATION SUMMARY:")
        print(f"  Status: {validation_result_dict.get('status', 'N/A')}")
        print(f"  Valid: {validation_result_dict.get('success', False)}")
        print(f"  Data Quality Score: {validation_result_dict.get('data_quality', {}).get('score', 'N/A')}")
        
        errors = validation_result_dict.get('validation_errors', [])
        if errors:
            print(f"\n  ❌ Errors Found ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                print(f"     {i}. {error}")
        
        warnings = validation_result_dict.get('validation_warnings', [])
        if warnings:
            print(f"\n  ⚠️  Warnings ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"     {i}. {warning}")
        
    except Exception as e:
        print(f"\n❌ ERROR in validation: {e}")
        return
    
    print("\n" + "="*80)
    print("✅ QUICK TEST COMPLETED")
    print("="*80 + "\n")


async def interactive_test():
    """Interactive mode - prompt user for test number"""
    
    print("\n" + "="*80)
    print("INTERACTIVE QUICK TESTER")
    print("="*80)
    print("\nThis tool runs a single test case through the agent pipeline.")
    print("You can see detailed output for debugging.\n")
    
    while True:
        try:
            user_input = input("Enter test number (1-50) or 'q' to quit: ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                print("Exiting...")
                break
            
            test_num = int(user_input)
            
            if test_num < 1 or test_num > 50:
                print("❌ Please enter a number between 1 and 50")
                continue
            
            await quick_test(test_num)
            
            print("\n" + "-"*80 + "\n")
            
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Command line mode: python quick_test.py 15
        try:
            test_number = int(sys.argv[1])
            asyncio.run(quick_test(test_number))
        except ValueError:
            print("Usage: python quick_test.py <test_number>")
            print("Example: python quick_test.py 15")
    else:
        # Interactive mode
        asyncio.run(interactive_test())