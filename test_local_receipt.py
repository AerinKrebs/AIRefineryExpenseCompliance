import asyncio
import json
import base64
import os
import sys
from pathlib import Path
import traceback

# Import your agent
from agents import image_understanding_agent, validation_agent
from audit import audit_log


def encode_image_to_base64(image_path: str) -> str:
    """
    Read an image file and convert it to base64 string.
    
    Parameters:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_type(image_path: str) -> str:
    """Determine if image is a receipt or invoice based on filename"""
    filename = os.path.basename(image_path).lower()
    if "invoice" in filename:
        return "invoice"
    return "receipt"


def print_separator(title: str = ""):
    """Print a visual separator"""
    print("\n" + "=" * 60)
    if title:
        print(f" {title}")
        print("=" * 60)

def print_verificaion_data(data):
    if not data:
        print("No data extracted")
        return

    print("\n  --- Validation Data ---")

    # If it's a LIST, print each item
    if isinstance(data, list):
        for item in data:
            print(f"  - {item}")
        return

    # Otherwise treat as dict
    for key, value in data.items():
        print(f"  {key}: {value}")

def print_extracted_data(data: dict):
    """Pretty print the extracted data"""
    if not data:
        print("No data extracted")
        return
    
    print(f"\n  Vendor: {data.get('vendor_name', 'N/A')}")
    print(f"  Address: {data.get('vendor_address', 'N/A')}")
    print(f"  Date: {data.get('date', 'N/A')}")
    print(f"  Time: {data.get('time', 'N/A')}")
    print(f"  Currency: {data.get('currency', 'N/A')}")
    
    print(f"\n  --- Amounts ---")
    print(f"  Subtotal: ${data.get('subtotal', 'N/A')}")
    print(f"  Tax: ${data.get('tax_amount', 'N/A')}")
    print(f"  Tip: ${data.get('tip_amount', 'N/A')}")
    print(f"  TOTAL: ${data.get('total_amount', 'N/A')}")
    
    print(f"\n  --- Payment ---")
    print(f"  Method: {data.get('payment_method', 'N/A')}")
    print(f"  Card Last 4: {data.get('card_last_four', 'N/A')}")
    
    print(f"\n  --- Classification ---")
    print(f"  Category: {data.get('expense_category', 'N/A')}")
    print(f"  Confidence: {data.get('confidence_score', 'N/A')}%")
    
    # Line items
    line_items = data.get('line_items', [])
    if line_items:
        print(f"\n  --- Line Items ({len(line_items)}) ---")
        for i, item in enumerate(line_items, 1):
            desc = item.get('description', 'Unknown')
            qty = item.get('quantity', 1)
            total = item.get('total', 0)
            print(f"  {i}. {desc} (x{qty}) - ${total}")
    
    # Notes
    notes = data.get('notes')
    if notes:
        print(f"\n  Notes: {notes}")


async def test_receipt(image_path: str, user_id: str = "test_user"):
    """
    Test the image understanding agent with a local receipt image.
    
    Parameters:
        image_path: Path to the receipt image file
    """
    # Validate file exists
    if not os.path.exists(image_path):
        print(f"ERROR: File not found: {image_path}")
        return False
    
    # Get file info
    file_size = os.path.getsize(image_path)
    file_ext = Path(image_path).suffix.lower()
    
    print_separator("IMAGE UNDERSTANDING AGENT TEST")
    print(f"\n  File: {image_path}")
    print(f"  Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"  Type: {file_ext}")
    
    # Validate file type
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    if file_ext not in valid_extensions:
        print(f"\n  WARNING: File extension '{file_ext}' may not be supported.")
        print(f"  Supported types: {', '.join(valid_extensions)}")
    
    # Encode image
    print_separator("ENCODING IMAGE")
    try:
        image_base64 = encode_image_to_base64(image_path)
        print(f"  Base64 length: {len(image_base64):,} characters")
    except Exception as e:
        print(f"  ERROR encoding image: {e}")
        return False
    
    # Determine image type
    image_type = get_image_type(image_path)
    print(f"  Detected type: {image_type}")
    
    # Call the agent
    print_separator("CALLING IMAGE UNDERSTANDING AGENT")
    print("  Processing... (this may take a moment)")
    
    try:
        result = await image_understanding_agent(
            query="Please extract all expense information from this receipt image.",
            env_variable={
                "image_data": image_base64,
                "image_type": image_type
            },
            chat_history=None
        )
    except Exception as e:
        print(f"\n  ERROR calling agent: {e}")
        traceback.print_exc()
        return False

    #put validation agent with memory here
    try:
        valid = await validation_agent(
            query="Please validate the extracted expense information for accuracy and completeness.",
            env_variable={
                "extracted_data": json.loads(result)
            },
            chat_history=None
        )

    except Exception as e:
        print(f"\n  ERROR calling agent: {e}")
        traceback.print_exc()
        return False
    
    # Parse response
    print_separator("AGENT RESPONSE")
    print(f"\n  Raw Response:\n{result}\n")
    print(f"\n  Validation Response:\n{valid}\n")
   
    
    # Parse and display formatted results
    print_separator("IMAGE UNDERSTANDING RESULTS")
    try:
        parsed = json.loads(result)
        
        print(f"\n  Success: {parsed.get('success', 'N/A')}")
        
        if parsed.get('error'):
            print(f"  Error: {parsed.get('error')}")
        
        if parsed.get('success'):
            extracted_data = parsed.get('extracted_data', {})
            print_extracted_data(extracted_data)
            
            # Processing notes
            notes = parsed.get('processing_notes', [])
            if notes:
                print(f"\n  --- Processing Notes ---")
                for note in notes:
                    print(f"  • {note}")
    
        
    except json.JSONDecodeError as e:
        print(f"  ERROR: Could not parse response as JSON: {e}")
        return False
    
    try: 
        parsed_valid = json.loads(valid)
        print_separator("VALIDATION RESULTS")
        print(f"\n  Validation Success: {parsed_valid.get('success', 'N/A')}")
        print(parsed_valid["validation_details"]["data_quality_notes"])
        print("\n  Validation Errors:")
        print(parsed_valid["validation_details"]["validation_errors"])


    except json.JSONDecodeError as e:
        print(f"  ERROR: Could not parse validation response as JSON: {e}")
        return False
    
    print_separator("TEST COMPLETE")
    return True


async def interactive_mode():
    """Interactive mode - prompt user for image path"""
    print_separator("IMAGE UNDERSTANDING AGENT - INTERACTIVE TEST")
    
    while True:
        print("\nEnter the path to a receipt image (or 'quit' to exit):")
        image_path = input("> ").strip()
        
        # Remove quotes if user copied path with quotes
        image_path = image_path.strip('"').strip("'")
        
        if image_path.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not image_path:
            print("No path entered. Please try again.")
            continue
        
        await test_receipt(image_path)
        
        print("\n" + "-"*40)
        input("Press Enter to test another image...")


def print_usage():
    """Print usage instructions"""
    print("""
IMAGE UNDERSTANDING AGENT - LOCAL RECEIPT TEST
==============================================

Usage:
    python test_local_receipt.py <image_path>     Test a specific image
    python test_local_receipt.py --interactive    Interactive mode
    python test_local_receipt.py                  Show this help

Examples:
    python test_local_receipt.py receipt.jpg
    python test_local_receipt.py "C:\\Users\\aerin.krebs\\Documents\\receipt.png"
    python test_local_receipt.py ./test_images/lunch_receipt.jpg

Supported image formats:
    .jpg, .jpeg, .png, .gif, .webp, .bmp
""")

audit_log.print_summary()


# ==================== MAIN ====================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg in ['--help', '-h', 'help']:
            print_usage()
        elif arg in ['--interactive', '-i', 'interactive']:
            asyncio.run(interactive_mode())
        else:
            # Treat as file path
            image_path = arg
            # Remove quotes if present
            image_path = image_path.strip('"').strip("'")
            asyncio.run(test_receipt(image_path))
    else:
        print_usage()
        print("\nStarting interactive mode...\n")
        asyncio.run(interactive_mode())


audit_log.print_summary()