import asyncio
import json

from agents import validation_agent


def run_validation(env):
    return json.loads(asyncio.run(validation_agent("Validate expense", env)))


def test_routine_auto_approve():
    env = {
        "expense": {"vendor_name": "Hotel Simple", "date": "2025-12-01", "total_amount": 300, "expense_category": "lodging"},
        "attachments": ["receipt.jpg"],
        # routine_threshold default is 500 so 300 should be auto-approvable
    }
    res = run_validation(env)
    assert res["success"] is True
    assert res["auto_approved"] is True
    assert res["status"] == "auto_approved"
    assert "auto_approved_routine" in res["flags"]


def test_incomplete_reporting():
    env = {
        "expense": {"vendor_name": "Vendor X", "expense_category": "meals"},
        "attachments": ["receipt.jpg"],
    }
    res = run_validation(env)
    assert res["success"] is True
    assert "incomplete_reporting" in res["flags"]
    assert res["status"] == "needs_correction"


def test_high_value_routing():
    env = {
        "expense": {"vendor_name": "Consulting Co", "date": "2025-12-01", "total_amount": 2500, "expense_category": "other"},
        # No attachments and no justification provided -> should route for higher approval
    }
    res = run_validation(env)
    assert res["success"] is True
    # Must include high_value_missing_justification and high_value_missing_receipt flags
    assert any(f.startswith("high_value_missing_") for f in res["flags"]) or "high_value_missing_receipt" in res["flags"]
    assert "route_for_higher_approval" in res["flags"]
    assert res["status"] == "requires_higher_approval"


def test_lodging_limit_exceeded():
    # 3 nights, total $900 -> per-night $300 > default limit 200
    env = {
        "expense": {"vendor_name": "Hotel Lux", "date": "2025-12-01", "total_amount": 900, "expense_category": "lodging", "nights": 3},
        "attachments": ["receipt.jpg"],
    }
    res = run_validation(env)
    assert res["success"] is True
    assert "lodging_limit_exceeded" in res["flags"]
    assert res["status"] == "requires_higher_approval"


def test_missing_receipt_needs_correction():
    env = {
        "expense": {"vendor_name": "Office Supplies", "date": "2025-12-02", "total_amount": 45, "expense_category": "supplies"},
        # No attachments
    }
    res = run_validation(env)
    assert res["success"] is True
    assert "missing_receipt" in res["flags"]
    assert res["status"] == "needs_correction"
