import asyncio
import json
import os
import sys

# Ensure project root (parent folder) is on sys.path so imports like `from agents import ...` work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import validation_agent


def run(env):
    return json.loads(asyncio.run(validation_agent("Validate expense", env)))


def check_case(name, env, expected):
    print(f"\n--- {name} ---")
    res = run(env)
    print(json.dumps(res, indent=2))
    ok = True
    for k, v in expected.items():
        actual = res.get(k)
        if isinstance(v, list):
            # check that all expected items are in actual list
            for item in v:
                if item not in actual:
                    print(f"  FAIL: expected '{item}' in {k}, actual: {actual}")
                    ok = False
        else:
            if actual != v:
                print(f"  FAIL: expected {k} == {v}, actual: {actual}")
                ok = False
    if ok:
        print("  PASS")
    return ok


cases = [
    ("routine_auto_approve", {
        "expense": {"vendor_name": "Hotel Simple", "date": "2025-12-01", "total_amount": 300, "expense_category": "lodging"},
        "attachments": ["receipt.jpg"],
    }, {"auto_approved": True, "status": "auto_approved"}),

    ("incomplete_reporting", {
        "expense": {"vendor_name": "Vendor X", "expense_category": "meals"},
        "attachments": ["receipt.jpg"],
    }, {"status": "needs_correction", "flags": ["incomplete_reporting"]}),

    ("high_value_routing", {
        "expense": {"vendor_name": "Consulting Co", "date": "2025-12-01", "total_amount": 2500, "expense_category": "other"},
    }, {"status": "requires_higher_approval", "flags": ["route_for_higher_approval"]}),

    ("lodging_limit_exceeded", {
        "expense": {"vendor_name": "Hotel Lux", "date": "2025-12-01", "total_amount": 900, "expense_category": "lodging", "nights": 3},
        "attachments": ["receipt.jpg"],
    }, {"status": "requires_higher_approval", "flags": ["lodging_limit_exceeded"]}),

    ("missing_receipt", {
        "expense": {"vendor_name": "Office Supplies", "date": "2025-12-02", "total_amount": 45, "expense_category": "supplies"},
    }, {"status": "needs_correction", "flags": ["missing_receipt"]}),
]

all_ok = True
for name, env, expected in cases:
    ok = check_case(name, env, expected)
    all_ok = all_ok and ok

print('\nALL OK' if all_ok else '\nSOME FAILURES')
