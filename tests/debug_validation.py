import asyncio
import json
from agents import validation_agent

async def debug_test():
    """Debug what the validation agent actually returns"""
    
    test_data = {
        "vendor_name": "Starbucks Coffee",
        "vendor_address": "123 Main St, Seattle WA 98101",
        "date": "2024-12-01",
        "time": "14:30",
        "currency": "USD",
        "subtotal": 15.50,
        "tax_amount": 1.40,
        "tip_amount": 3.00,
        "total_amount": 19.90,
        "payment_method": "credit",
        "card_last_four": "4242",
        "line_items": [
            {
                "description": "Grande Latte",
                "quantity": 2,
                "unit_price": 5.75,
                "total": 11.50
            }
        ],
        "expense_category": "meals",
        "confidence_score": 95,
        "raw_text_extracted": "STARBUCKS\n123 Main St\nSeattle WA 98101",
        "notes": "Clear receipt"
    }
    
    env_variable = {
        "extracted_data": test_data,
        "user_id": "debug_user"
    }
    
    print("=" * 80)
    print("DEBUGGING VALIDATION AGENT")
    print("=" * 80)
    
    try:
        result_json = await validation_agent(
            query="Validate this expense data for compliance",
            env_variable=env_variable
        )
        
        print("\n--- RAW RESULT (first 1000 chars) ---")
        print(result_json[:1000])
        
        print("\n--- PARSED RESULT ---")
        result = json.loads(result_json)
        print(json.dumps(result, indent=2))
        
        print("\n--- CHECKING STRUCTURE ---")
        print(f"Has 'validation_details': {('validation_details' in result)}")
        if 'validation_details' in result:
            print(f"validation_details keys: {result['validation_details'].keys()}")
            print(f"validation_status: {result['validation_details'].get('validation_status')}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_test())