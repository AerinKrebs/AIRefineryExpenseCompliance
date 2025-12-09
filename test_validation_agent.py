"""
test_validation_agent.py

Test suite for the validation agent.
Run this after your image understanding agent tests to validate the extracted data.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

# Import your agents
from agents import validation_agent


class ValidationAgentTester:
    """Test harness for validation agent"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.audit_log_path = Path("audit_log.json")
    
    def get_latest_audit_entry(self) -> Dict[Any, Any]:
        """Get the most recent entry from audit_log.json"""
        try:
            with open(self.audit_log_path, 'r') as f:
                audit_data = json.load(f)
                if audit_data.get("entries"):
                    return audit_data["entries"][-1]  # Get last entry
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not read audit log: {e}")
        return {}
    
    def map_status_to_expected(self, actual_status: str) -> str:
        """Map the agent's status to our expected test statuses"""
        status_mapping = {
            "approved": "PASS",
            "needs_correction": "FAIL",
            "incomplete_data": "FAIL",
        }
        return status_mapping.get(actual_status, "UNKNOWN")
    
    def extract_error_details(self, validation_errors: list) -> list:
        """Extract detailed error information from validation errors"""
        error_details = []
        for error in validation_errors:
            if isinstance(error, dict):
                error_details.append({
                    "field": error.get("field", "unknown"),
                    "issue": error.get("issue", str(error)),
                    "severity": error.get("severity", "unknown"),
                    "current_value": error.get("current_value"),
                    "expected": error.get("expected")
                })
            else:
                error_details.append({
                    "field": "unknown",
                    "issue": str(error),
                    "severity": "unknown",
                    "current_value": None,
                    "expected": None
                })
        return error_details
    
    def extract_warning_details(self, validation_warnings: list) -> list:
        """Extract detailed warning information from validation warnings"""
        warning_details = []
        for warning in validation_warnings:
            if isinstance(warning, dict):
                warning_details.append({
                    "field": warning.get("field", "unknown"),
                    "issue": warning.get("issue", str(warning)),
                    "recommendation": warning.get("recommendation", "")
                })
            else:
                warning_details.append({
                    "field": "unknown",
                    "issue": str(warning),
                    "recommendation": ""
                })
        return warning_details
        
    async def run_validation_test(
        self, 
        test_name: str, 
        extracted_data: Dict[Any, Any], 
        expected_status: str,
        expected_error_fields: list = None,
        user_id: str = "test_user"
    ) -> Dict[Any, Any]:
        """
        Run a single validation test
        
        Args:
            test_name: Name of the test case
            extracted_data: The data to validate
            expected_status: Expected validation status (PASS/FAIL)
            expected_error_fields: Fields expected to have errors
            user_id: User ID for audit logging
        
        Returns:
            Test result dictionary
        """
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"{'='*80}")
        
        env_variable = {
            "extracted_data": extracted_data,
            "user_id": user_id
        }
        
        try:
            # Run validation
            result_json = await validation_agent(
                query="Validate this expense data for compliance",
                env_variable=env_variable
            )
            
            # Get the result from audit log (most recent entry)
            audit_entry = self.get_latest_audit_entry()
            
            if not audit_entry:
                raise Exception("No audit log entry found")
            
            # Extract validation data from the new structure
            validation_data = audit_entry.get("data", {})
            actual_status_raw = validation_data.get("status", "UNKNOWN")
            actual_status = self.map_status_to_expected(actual_status_raw)
            
            # Get validation details
            validation_details = validation_data.get("validation_details", {})
            
            # Extract errors and warnings from the validation_details
            raw_errors = validation_details.get("validation_errors", [])
            raw_warnings = validation_details.get("validation_warnings", [])
            
            error_details = self.extract_error_details(raw_errors)
            warning_details = self.extract_warning_details(raw_warnings)
            
            # Get data quality info
            data_quality = validation_data.get("data_quality", {})
            quality_score = data_quality.get("score", 0)
            quality_summary = data_quality.get("summary", {})
            
            # Check if result matches expectation
            status_match = actual_status == expected_status
            
            # Check if expected error fields are present
            error_fields_found = [err["field"] for err in error_details]
            field_match = True
            if expected_error_fields:
                field_match = all(field in error_fields_found for field in expected_error_fields)
            
            test_passed = status_match and field_match
            
            if test_passed:
                self.passed += 1
                status_icon = "✅ PASS"
            else:
                self.failed += 1
                status_icon = "❌ FAIL"
            
            test_result = {
                "test_name": test_name,
                "passed": test_passed,
                "status_match": status_match,
                "field_match": field_match,
                "expected_status": expected_status,
                "actual_status": actual_status,
                "actual_status_raw": actual_status_raw,
                "expected_error_fields": expected_error_fields or [],
                "actual_error_fields": error_fields_found,
                "errors": error_details,
                "warnings": warning_details,
                "data_quality_score": quality_score,
                "quality_summary": quality_summary,
                "full_result": validation_data
            }
            
            self.test_results.append(test_result)
            
            # Print detailed summary
            print(f"\n{status_icon}")
            print(f"Expected Status: {expected_status}, Got: {actual_status} (raw: {actual_status_raw})")
            
            if expected_error_fields:
                print(f"\nExpected Error Fields: {', '.join(expected_error_fields)}")
                print(f"Actual Error Fields: {', '.join(error_fields_found)}")
                if not field_match:
                    missing = set(expected_error_fields) - set(error_fields_found)
                    if missing:
                        print(f"⚠️  Missing expected errors on: {', '.join(missing)}")
            
            print(f"\nData Quality Score: {quality_score}/100")
            print(f"Total Errors: {len(error_details)} (Critical: {quality_summary.get('critical_errors', 0)})")
            print(f"Total Warnings: {len(warning_details)}")
            
            if error_details:
                print(f"\n📋 Validation Errors ({len(error_details)}):")
                for i, error in enumerate(error_details[:5], 1):  # Show first 5
                    print(f"  {i}. [{error['severity']}] {error['field']}: {error['issue']}")
                    if error['current_value'] is not None:
                        print(f"     Current: {error['current_value']}")
                    if error['expected']:
                        print(f"     Expected: {error['expected']}")
            
            if warning_details:
                print(f"\n⚠️  Validation Warnings ({len(warning_details)}):")
                for i, warning in enumerate(warning_details[:5], 1):  # Show first 5
                    print(f"  {i}. {warning['field']}: {warning['issue']}")
                    if warning['recommendation']:
                        print(f"     → {warning['recommendation']}")
            
            # Show corrections if any were made
            corrections = validation_details.get("corrections_made", [])
            if corrections:
                print(f"\n🔧 Corrections Made ({len(corrections)}):")
                for i, correction in enumerate(corrections[:3], 1):
                    print(f"  {i}. {correction.get('field')}: {correction.get('original_value')} → {correction.get('corrected_value')}")
                    print(f"     Reason: {correction.get('reason')}")
            
            return test_result
            
        except Exception as e:
            self.failed += 1
            print(f"\n❌ TEST ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            test_result = {
                "test_name": test_name,
                "passed": False,
                "error": str(e),
                "expected_status": expected_status,
                "actual_status": "ERROR"
            }
            self.test_results.append(test_result)
            return test_result
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        print(f"{'='*80}\n")
        
        # Show failed tests with details
        if self.failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result.get("passed"):
                    print(f"\n  {result['test_name']}")
                    print(f"    Expected: {result['expected_status']}, Got: {result.get('actual_status')}")
                    
                    if not result.get("status_match"):
                        print(f"    ⚠️  Status mismatch")
                    
                    if not result.get("field_match"):
                        print(f"    ⚠️  Error field mismatch")
                        expected = set(result.get("expected_error_fields", []))
                        actual = set(result.get("actual_error_fields", []))
                        missing = expected - actual
                        unexpected = actual - expected
                        if missing:
                            print(f"       Missing: {', '.join(missing)}")
                        if unexpected:
                            print(f"       Unexpected: {', '.join(unexpected)}")


def load_external_test_cases() -> list:
    """Load external test cases if present in tests/extracted_outputs.json or tests/validation_test_cases.json.
    Supported shapes:
      - a single object representing extracted_data
      - a list of objects where each object is either the extracted_data dict or
        an envelope {"extracted_data": {...}, "expected_status": "PASS", "expected_error_fields": [...]}.
    Returns a list of envelopes with keys: extracted_data, expected_status, expected_error_fields
    """
    candidates = [
        Path("tests/extracted_outputs.json"),
        Path("tests/validation_test_cases.json"),
        Path("validation_test_cases.json")
    ]

    for p in candidates:
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue

            cases = []
            if isinstance(raw, dict):
                # If the dict looks like an envelope
                if raw.get("extracted_data"):
                    envelope = {
                        "extracted_data": raw.get("extracted_data"),
                        "expected_status": raw.get("expected_status", "PASS"),
                        "expected_error_fields": raw.get("expected_error_fields", [])
                    }
                    cases.append(envelope)
                else:
                    # Treat the whole dict as extracted_data
                    cases.append({
                        "extracted_data": raw,
                        "expected_status": "PASS",
                        "expected_error_fields": []
                    })

            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict) and item.get("extracted_data"):
                        cases.append({
                            "extracted_data": item.get("extracted_data"),
                            "expected_status": item.get("expected_status", "PASS"),
                            "expected_error_fields": item.get("expected_error_fields", [])
                        })
                    elif isinstance(item, dict):
                        cases.append({
                            "extracted_data": item,
                            "expected_status": "PASS",
                            "expected_error_fields": []
                        })
            if cases:
                print(f"Loaded {len(cases)} external test case(s) from {p}")
                return cases

    return []


# ========================================== TEST CASES ===========================================

async def test_valid_receipt():
    """Test Case 1: Perfectly valid receipt data"""
    return {
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
            },
            {
                "description": "Blueberry Muffin",
                "quantity": 1,
                "unit_price": 4.00,
                "total": 4.00
            }
        ],
        "expense_category": "meals",
        "confidence_score": 95,
        "raw_text_extracted": "STARBUCKS\n123 Main St\nSeattle WA 98101\n\nGrande Latte x2 $11.50\nBlueberry Muffin x1 $4.00\n\nSubtotal: $15.50\nTax: $1.40\nTip: $3.00\nTotal: $19.90\n\nVisa ****4242",
        "notes": "Clear receipt, all fields legible"
    }


async def test_missing_total():
    """Test Case 2: Missing critical field - total_amount"""
    return {
        "vendor_name": "Bob's Hardware",
        "vendor_address": "456 Oak Ave, Portland OR 97201",
        "date": "2024-11-28",
        "time": None,
        "currency": "USD",
        "subtotal": 45.99,
        "tax_amount": 4.14,
        "tip_amount": None,
        "total_amount": None,  # MISSING CRITICAL FIELD
        "payment_method": "debit",
        "card_last_four": "8765",
        "line_items": [
            {
                "description": "Paint Roller Set",
                "quantity": 1,
                "unit_price": 25.99,
                "total": 25.99
            },
            {
                "description": "Masking Tape",
                "quantity": 2,
                "unit_price": 10.00,
                "total": 20.00
            }
        ],
        "expense_category": "supplies",
        "confidence_score": 85,
        "raw_text_extracted": "Bob's Hardware\n456 Oak Ave Portland OR\nPaint Roller Set $25.99\nMasking Tape x2 $20.00\nSubtotal $45.99\nTax $4.14",
        "notes": "Bottom of receipt cut off"
    }


async def test_calculation_mismatch():
    """Test Case 3: Total doesn't match subtotal + tax"""
    return {
        "vendor_name": "Pizza Palace",
        "vendor_address": "789 Broadway, New York NY 10003",
        "date": "2024-12-02",
        "time": "19:45",
        "currency": "USD",
        "subtotal": 30.00,
        "tax_amount": 2.70,
        "tip_amount": 5.00,
        "total_amount": 42.00,  # Should be 37.70 (30 + 2.70 + 5)
        "payment_method": "credit",
        "card_last_four": "1234",
        "line_items": [
            {
                "description": "Large Pepperoni Pizza",
                "quantity": 1,
                "unit_price": 18.00,
                "total": 18.00
            },
            {
                "description": "Caesar Salad",
                "quantity": 1,
                "unit_price": 12.00,
                "total": 12.00
            }
        ],
        "expense_category": "meals",
        "confidence_score": 80,
        "raw_text_extracted": "PIZZA PALACE\n789 Broadway NYC\n\nLarge Pepperoni $18.00\nCaesar Salad $12.00\n\nSubtotal: $30.00\nTax: $2.70\nTip: $5.00\nTOTAL: $42.00",
        "notes": "Receipt slightly blurry"
    }


async def test_invalid_date_format():
    """Test Case 4: Invalid date format"""
    return {
        "vendor_name": "Office Supplies Co",
        "vendor_address": "321 Market St, San Francisco CA 94102",
        "date": "12/03/24",  # Wrong format, should be YYYY-MM-DD
        "time": "10:15",
        "currency": "USD",
        "subtotal": 125.00,
        "tax_amount": 11.25,
        "tip_amount": None,
        "total_amount": 136.25,
        "payment_method": "credit",
        "card_last_four": "9999",
        "line_items": [
            {
                "description": "Paper Reams (10)",
                "quantity": 10,
                "unit_price": 8.50,
                "total": 85.00
            },
            {
                "description": "Stapler Heavy Duty",
                "quantity": 2,
                "unit_price": 20.00,
                "total": 40.00
            }
        ],
        "expense_category": "supplies",
        "confidence_score": 90,
        "raw_text_extracted": "Office Supplies Co\n321 Market St SF CA\n12/03/24 10:15 AM\n\nPaper Reams x10 $85.00\nHeavy Duty Stapler x2 $40.00\n\nSubtotal $125.00\nTax $11.25\nTotal $136.25",
        "notes": "Clean scan"
    }


async def test_line_items_mismatch():
    """Test Case 5: Line items don't sum to subtotal"""
    return {
        "vendor_name": "Tech Store",
        "vendor_address": "555 Tech Blvd, Austin TX 78701",
        "date": "2024-11-30",
        "time": "16:20",
        "currency": "USD",
        "subtotal": 299.99,
        "tax_amount": 24.00,
        "tip_amount": None,
        "total_amount": 323.99,
        "payment_method": "credit",
        "card_last_four": "5555",
        "line_items": [
            {
                "description": "Wireless Mouse",
                "quantity": 1,
                "unit_price": 49.99,
                "total": 49.99
            },
            {
                "description": "USB-C Cable",
                "quantity": 2,
                "unit_price": 19.99,
                "total": 39.98
            }
            # Line items sum to $89.97, but subtotal is $299.99
        ],
        "expense_category": "supplies",
        "confidence_score": 75,
        "raw_text_extracted": "Tech Store\n555 Tech Blvd Austin\nWireless Mouse $49.99\nUSB-C Cable x2 $39.98\n[RECEIPT TORN]\nSubtotal $299.99\nTax $24.00\nTotal $323.99",
        "notes": "Middle section of receipt torn/unreadable"
    }


async def test_future_date():
    """Test Case 6: Date in the future"""
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "vendor_name": "Restaurant XYZ",
        "vendor_address": "100 Food St, Chicago IL 60601",
        "date": future_date,  # Future date
        "time": "12:00",
        "currency": "USD",
        "subtotal": 55.00,
        "tax_amount": 5.50,
        "tip_amount": 11.00,
        "total_amount": 71.50,
        "payment_method": "credit",
        "card_last_four": "7777",
        "line_items": [
            {
                "description": "Lunch Special",
                "quantity": 2,
                "unit_price": 27.50,
                "total": 55.00
            }
        ],
        "expense_category": "meals",
        "confidence_score": 85,
        "raw_text_extracted": f"Restaurant XYZ\n100 Food St Chicago\n{future_date} 12:00\nLunch Special x2 $55.00\nSubtotal $55.00\nTax $5.50\nTip $11.00\nTotal $71.50",
        "notes": "Date seems incorrect"
    }


async def test_negative_amounts():
    """Test Case 7: Negative amounts (invalid)"""
    return {
        "vendor_name": "Gas Station",
        "vendor_address": "999 Highway 1, Los Angeles CA 90001",
        "date": "2024-12-01",
        "time": "08:30",
        "currency": "USD",
        "subtotal": 50.00,
        "tax_amount": -5.00,  # Negative tax (invalid)
        "tip_amount": None,
        "total_amount": 45.00,
        "payment_method": "credit",
        "card_last_four": "3333",
        "line_items": [
            {
                "description": "Gasoline",
                "quantity": 12.5,
                "unit_price": 4.00,
                "total": 50.00
            }
        ],
        "expense_category": "travel",
        "confidence_score": 70,
        "raw_text_extracted": "Gas Station\n999 Highway 1 LA\nGasoline 12.5 gal @ $4.00\nSubtotal $50.00\nTax -$5.00\nTotal $45.00",
        "notes": "OCR may have misread refund as negative"
    }


async def test_invalid_card_number():
    """Test Case 8: Invalid card last four digits"""
    return {
        "vendor_name": "Grocery Store",
        "vendor_address": "200 Main St, Denver CO 80201",
        "date": "2024-12-03",
        "time": "17:00",
        "currency": "USD",
        "subtotal": 87.50,
        "tax_amount": 7.88,
        "tip_amount": None,
        "total_amount": 95.38,
        "payment_method": "credit",
        "card_last_four": "12",  # Should be 4 digits
        "line_items": [
            {
                "description": "Groceries",
                "quantity": 1,
                "unit_price": 87.50,
                "total": 87.50
            }
        ],
        "expense_category": "meals",
        "confidence_score": 80,
        "raw_text_extracted": "Grocery Store\n200 Main St Denver\nGroceries $87.50\nSubtotal $87.50\nTax $7.88\nTotal $95.38\nCard **12",
        "notes": "Card number partially readable"
    }


async def test_missing_vendor():
    """Test Case 9: Missing vendor name"""
    return {
        "vendor_name": None,  # Missing critical field
        "vendor_address": "Unknown",
        "date": "2024-12-01",
        "time": None,
        "currency": "USD",
        "subtotal": 25.00,
        "tax_amount": 2.25,
        "tip_amount": None,
        "total_amount": 27.25,
        "payment_method": "cash",
        "card_last_four": None,
        "line_items": [],
        "expense_category": "other",
        "confidence_score": 45,
        "raw_text_extracted": "[FADED RECEIPT]\n...some items...\nSubtotal $25.00\nTax $2.25\nTotal $27.25\nCash",
        "notes": "Receipt heavily faded, vendor info unreadable"
    }


async def test_low_confidence_score():
    """Test Case 10: Low confidence score with multiple issues"""
    return {
        "vendor_name": "Café unclear",
        "vendor_address": None,
        "date": "2024-11-25",
        "time": None,
        "currency": "USD",
        "subtotal": 12.00,
        "tax_amount": None,
        "tip_amount": None,
        "total_amount": 14.50,
        "payment_method": None,
        "card_last_four": None,
        "line_items": [],
        "expense_category": "meals",
        "confidence_score": 35,  # Very low confidence
        "raw_text_extracted": "...fé...\n...coffee... $12...\n...Total... $14.50...",
        "notes": "Receipt water damaged, most text unreadable"
    }


async def test_wrong_currency():
    """Test Case 11: Invalid currency code"""
    return {
        "vendor_name": "International Store",
        "vendor_address": "123 Global St, Boston MA 02101",
        "date": "2024-12-02",
        "time": "14:00",
        "currency": "XYZ",  # Invalid currency code
        "subtotal": 100.00,
        "tax_amount": 10.00,
        "tip_amount": None,
        "total_amount": 110.00,
        "payment_method": "credit",
        "card_last_four": "6666",
        "line_items": [
            {
                "description": "Product A",
                "quantity": 1,
                "unit_price": 100.00,
                "total": 100.00
            }
        ],
        "expense_category": "supplies",
        "confidence_score": 80,
        "raw_text_extracted": "International Store\n123 Global St Boston\nProduct A 100.00 XYZ\nSubtotal 100.00\nTax 10.00\nTotal 110.00",
        "notes": "Currency symbol unclear"
    }


async def test_large_expense_amount():
    """Test Case 12: Unusually large expense amount"""
    return {
        "vendor_name": "Electronics Wholesale",
        "vendor_address": "500 Commerce Dr, Miami FL 33101",
        "date": "2024-12-01",
        "time": "11:30",
        "currency": "USD",
        "subtotal": 45000.00,  # Very large amount
        "tax_amount": 4050.00,
        "tip_amount": None,
        "total_amount": 49050.00,
        "payment_method": "check",
        "card_last_four": None,
        "line_items": [
            {
                "description": "Laptops (Bulk Order)",
                "quantity": 50,
                "unit_price": 900.00,
                "total": 45000.00
            }
        ],
        "expense_category": "supplies",
        "confidence_score": 95,
        "raw_text_extracted": "Electronics Wholesale\n500 Commerce Dr Miami\nLaptops (Bulk) 50 @ $900 = $45,000.00\nSubtotal $45,000.00\nTax $4,050.00\nTotal $49,050.00\nCheck Payment",
        "notes": "Large bulk purchase"
    }


# ========================================== RUN ALL TESTS ===========================================

async def run_all_tests():
    """Run all validation tests"""
    
    tester = ValidationAgentTester()
    
    print("\n" + "="*80)
    print("VALIDATION AGENT TEST SUITE - DATA VALIDATION ONLY")
    print("="*80)
    # If external extracted test cases are present, use them instead of hardcoded cases.
    external_cases = load_external_test_cases()
    if external_cases:
        for i, case in enumerate(external_cases, start=1):
            name = case.get("name") or f"External Case {i}"
            extracted = case.get("extracted_data")
            expected_status = case.get("expected_status", "PASS")
            expected_error_fields = case.get("expected_error_fields", [])

            await tester.run_validation_test(
                name,
                extracted,
                expected_status=expected_status,
                expected_error_fields=expected_error_fields
            )
    else:
        # Test 1: Valid receipt (should PASS - no data errors)
        await tester.run_validation_test(
            "Test 1: Valid Receipt",
            await test_valid_receipt(),
            expected_status="PASS",
            expected_error_fields=[]
        )
    
    # Test 2: Missing total (should FAIL with total_amount error)
    await tester.run_validation_test(
        "Test 2: Missing Total Amount",
        await test_missing_total(),
        expected_status="FAIL",
        expected_error_fields=["total_amount"]
    )
    
    # Test 3: Calculation mismatch (should FAIL with calculation error)
    await tester.run_validation_test(
        "Test 3: Calculation Mismatch",
        await test_calculation_mismatch(),
        expected_status="FAIL",
        expected_error_fields=["total_amount"]
    )
    
    # Test 4: Invalid date format (should FAIL with date error)
    await tester.run_validation_test(
        "Test 4: Invalid Date Format",
        await test_invalid_date_format(),
        expected_status="FAIL",
        expected_error_fields=["date"]
    )
    
    # Test 5: Line items mismatch (should FAIL with subtotal/line_items error)
    await tester.run_validation_test(
        "Test 5: Line Items Don't Sum",
        await test_line_items_mismatch(),
        expected_status="FAIL",
        expected_error_fields=["subtotal", "line_items"]
    )
    
    # Test 6: Future date (should FAIL with date error)
    await tester.run_validation_test(
        "Test 6: Future Date",
        await test_future_date(),
        expected_status="FAIL",
        expected_error_fields=["date"]
    )
    
    # Test 7: Negative amounts (should FAIL with tax_amount error)
    await tester.run_validation_test(
        "Test 7: Negative Amounts",
        await test_negative_amounts(),
        expected_status="FAIL",
        expected_error_fields=["tax_amount"]
    )
    
    # Test 8: Invalid card number (should FAIL with card_last_four error)
    await tester.run_validation_test(
        "Test 8: Invalid Card Number",
        await test_invalid_card_number(),
        expected_status="FAIL",
        expected_error_fields=["card_last_four"]
    )
    
    # Test 9: Missing vendor (should FAIL with vendor_name error)
    await tester.run_validation_test(
        "Test 9: Missing Vendor Name",
        await test_missing_vendor(),
        expected_status="FAIL",
        expected_error_fields=["vendor_name"]
    )
    
    # Test 10: Low confidence (should FAIL with confidence_score error)
    await tester.run_validation_test(
        "Test 10: Low Confidence Score",
        await test_low_confidence_score(),
        expected_status="FAIL",
        expected_error_fields=["confidence_score"]
    )
    
    # Test 11: Wrong currency (should FAIL with currency error)
    await tester.run_validation_test(
        "Test 11: Invalid Currency Code",
        await test_wrong_currency(),
        expected_status="FAIL",
        expected_error_fields=["currency"]
    )
    
    # Test 12: Large amount (should PASS - just a large number, not invalid)
    await tester.run_validation_test(
        "Test 12: Large Expense Amount",
        await test_large_expense_amount(),
        expected_status="PASS",  # Data is valid, policy agent will handle amount limits
        expected_error_fields=[]
    )
    
    # Print final summary
    tester.print_summary()
    
    # Save detailed results to file
    with open("validation_test_results.json", "w") as f:
        json.dump(tester.test_results, f, indent=2)
    print(f"Detailed results saved to: validation_test_results.json\n")
    
    return tester


# ========================================== MAIN ===========================================

if __name__ == "__main__":
    print("Starting Validation Agent Tests...\n")
    asyncio.run(run_all_tests())