import os
import yaml
import json
import pandas as pd
from air import AsyncAIRefinery, DistillerClient
from audit import audit_log
from dotenv import load_dotenv

# Load API Key & set other state variables
load_dotenv()
API_KEY = str(os.getenv("API_KEY"))
PROJECT_NAME = "ExpenseCompliance_AIRefinery_Project"

# Helper function that sends a prompt to a model hosted on AIR
async def get_model_response(prompt: str, model: str="openai/gpt-4o-mini") -> str:
    """
    Sends a prompt to a given model hosted in AI Refinery, then returns the result.

    Parameters:
        prompt (str): The prompt to send to the LLM.
        model (str): The ID of the LLM to use. Is openai/gpt-4o-mini by default

    Returns:
        str: The model's response.
    """

    client = AsyncAIRefinery(api_key=API_KEY)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    # Guard against missing/None content on the response object
    content = getattr(response.choices[0].message, "content", None) or ""
    return content.strip()

#=========================================== SUPPORTING FUNCTIONS ===========================================
#Function for vision model call to AIR
async def get_vision_model_response(prompt: str, image_data: str, model: str = "openai/gpt-4o") -> str:
    """
    Sends a prompt with an image to a vision-capable model hosted in AI Refinery.

    Parameters:
        prompt (str): The text prompt to send.
        image_data (str): Base64 encoded image data or image URL.
        model (str): The ID of the vision-capable LLM to use.

    Returns:
        str: The model's response.
    """
    client = AsyncAIRefinery(api_key=API_KEY)
    
    # Determine if image_data is a URL or base64
    if image_data.startswith(('http://', 'https://')):
        image_content = {"type": "image_url", "image_url": {"url": image_data}}
    else:
        # Assume base64 encoded image
        image_content = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
        }
    #result for vision model call
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    image_content
                ]
            }
        ]
    )
    # Guard against missing/None content on the response object
    content = getattr(response.choices[0].message, "content", None) or ""
    return content.strip()
# ========================================== AGENTS ===========================================

#Function for image understanding agent
async def image_understanding_agent(query: str, env_variable=None, chat_history=None) -> str:
    """
    Analyzes receipt/invoice images to extract structured expense data.

    Parameters:
        query (str): The user's query or instructions.
        env_variable (dict): Environment variables containing image data and form info.
        chat_history (list): Previous conversation history.

    Returns:
        str: JSON string containing extracted expense data.
    """
    # Extract image data from environment variables
    image_data = env_variable.get("image_data", "") if env_variable else ""
    image_type = env_variable.get("image_type", "unknown") if env_variable else "unknown"
    
    if not image_data:
        return json.dumps({
            "success": False,
            "error": "No image data provided",
            "extracted_data": None
        })
    
    # Build the extraction prompt
    extraction_prompt = f"""
        You are an expert receipt and invoice analyzer for expense compliance.
        Analyze this {image_type} image and extract all relevant expense information.

        User context: {query}

        Extract and return a JSON object with the following structure:
        {{
            "vendor_name": "string or null",
            "vendor_address": "string or null",
            "date": "YYYY-MM-DD or null",
            "time": "HH:MM or null",
            "currency": "USD/EUR/etc or null",
            "subtotal": number or null,
            "tax_amount": number or null,
            "tip_amount": number or null,
            "total_amount": number or null,
            "payment_method": "cash/credit/debit/etc or null",
            "card_last_four": "string or null",
            "line_items": [
                {{"description": "string", "quantity": number, "unit_price": number, "total": number}}
            ],
            "expense_category": "meals/travel/supplies/entertainment/lodging/other",
            "confidence_score": 0-100,
            "raw_text_extracted": "full OCR text from image",
            "notes": "any issues, unclear items, or observations"
        }}

        Important guidelines:
        1. Extract ALL visible text from the receipt
        2. Parse amounts carefully - watch for decimal points
        3. Identify the currency from symbols ($, €, £) or text
        4. Categorize the expense based on vendor type and items
        5. Note any quality issues (blurry, cut off, faded text)
        6. If multiple receipts in one image, process only the primary one and note others
        User context: {query}

        IMPORTANT: Return ONLY the raw JSON object. Do NOT wrap it in markdown code blocks or any other formatting.
        Return ONLY the JSON object, no additional text.
        """
    
    try:
        # Call vision model
        response = await get_vision_model_response(
            prompt=extraction_prompt,
            image_data=image_data,
            model="openai/gpt-4o"
        )
        
        # Parse response - handle markdown code blocks ============================ IGNORE========================
        try:
            clean_response = response.strip()
            # Remove markdown code blocks if present
            import re
            
            # Pattern to match ```json ... ``` or ``` ... ```
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, clean_response)
            
            if match:
                # Extract content from inside code blocks
                clean_response = match.group(1).strip()
            
            # Also handle case where there's no code block but starts/ends with ```
            if clean_response.startswith('```'):
                # Find the end of the first line (might be ```json or just ```)
                first_newline = clean_response.find('\n')
                if first_newline != -1:
                    clean_response = clean_response[first_newline + 1:]
            
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            clean_response = clean_response.strip()
            extracted_data = json.loads(clean_response)
            
        except json.JSONDecodeError as e:
            # If parsing still fails, return error with raw response
            return json.dumps({
                "success": False,
                "error": f"Failed to parse model response as JSON: {str(e)}",
                "raw_response": response,
                "extracted_data": None
            }, indent=2)
    # ============================ IGNORE========================
        # Add metadata for contextualization
        result = {
            "success": True,
            "extracted_data": extracted_data,
            "image_type": image_type,
            "processing_notes": []
        }
        # Save to audit log 
        audit_log.save(
            agent_name="Image Understanding Agent",
            result=result,
            user_id=(env_variable or {}).get("user_id", "unknown")
        )
    
        
        # Basic validation checks
        if extracted_data.get("total_amount") is None:
            result["processing_notes"].append("Warning: Could not extract total amount")
        
        if extracted_data.get("date") is None:
            result["processing_notes"].append("Warning: Could not extract transaction date")
        
        if extracted_data.get("vendor_name") is None:
            result["processing_notes"].append("Warning: Could not identify vendor")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "extracted_data": None
        })

# TODO: Function for critical thinking agent
async def critical_thinking_agent(query: str, env_variable=None, chat_history=None) -> str:
    return ""

# Validation Agent: ensures submitted expenses comply with org policies
async def validation_agent(query: str, env_variable=None, chat_history=None) -> str:
    """
    Validates a single expense report or expense item represented in `env_variable`.

    Expected input (env_variable):
      - expense: dict (extracted expense data) OR extracted_data in same shape as image_understanding_agent
      - attachments: list of receipt/attachment metadata (optional)
      - nights: int (for lodging) (optional)
      - justification: str (optional)
      - claimed_amount: number (optional)
      - policy_overrides: dict (optional) to override default limits

    Returns:
      JSON string with validation outcome, flags, and suggested actions.
    """

    # Defensive defaults
    env = env_variable or {}
    expense = env.get("expense") or env.get("extracted_data") or {}
    attachments = env.get("attachments") or env.get("receipts") or []

    # Policy defaults (can be overridden via env_variable.policy_overrides)
    policy = {
        "lodging_limit_per_night": 200.0,
        "airfare_limit": 1500.0,
        "high_value_threshold": 1000.0,
        "routine_threshold": 500.0,
        "min_receipt_amount": 0.01  # receipts required for any positive claim
    }
    overrides = env.get("policy_overrides") or {}
    policy.update(overrides)

    # Prepare result structure
    issues = []
    flags = []
    suggested_actions = []

    # Helper to safely get numeric total
    def _get_amount(src):
        try:
            if src is None:
                return None
            return float(src)
        except Exception:
            return None

    total_amount = _get_amount(expense.get("total_amount") or env.get("claimed_amount"))
    category = (expense.get("expense_category") or env.get("expense_category") or "other")
    category = category.lower() if isinstance(category, str) else "other"

    # Required fields check
    required_fields = ["date", "vendor_name", "expense_category"]
    missing_required = [f for f in required_fields if not expense.get(f)]
    if missing_required:
        issues.append(f"Missing required fields: {', '.join(missing_required)}")

    # Receipt attachment check
    receipts_present = len(attachments) > 0
    # Enforce receipts for any claimed positive amount
    if total_amount is not None and total_amount > 0 and not receipts_present:
        issues.append("Missing receipt(s) for claimed amount")
        flags.append("missing_receipt")
        suggested_actions.append("Attach receipt image(s) before submission")

    # Standard review: lodging
    if category in ("lodging",):
        # Only enforce per-night limits when 'nights' is explicitly provided
        nights_provided = None
        if "nights" in env:
            nights_provided = env.get("nights")
        elif "nights" in expense:
            nights_provided = expense.get("nights")

        if nights_provided is not None:
            try:
                nights = int(nights_provided) if nights_provided else 1
            except Exception:
                nights = 1

            if total_amount is not None:
                per_night = total_amount / max(1, nights)
                if per_night > policy["lodging_limit_per_night"]:
                    issues.append(f"Lodging per-night cost ${per_night:.2f} exceeds policy limit ${policy['lodging_limit_per_night']:.2f}")
                    flags.append("lodging_limit_exceeded")
                    suggested_actions.append("Provide justification or adjust lodging to policy-compliant rate")

    # Standard review: airfare / travel
    if category in ("airfare", "travel", "transportation"):
        if total_amount is not None and total_amount > policy["airfare_limit"]:
            issues.append(f"Airfare/Travel amount ${total_amount:.2f} exceeds policy limit ${policy['airfare_limit']:.2f}")
            flags.append("airfare_limit_exceeded")
            suggested_actions.append("Route to travel manager for exception approval")

    # Validate expense category
    valid_categories = {"meals", "travel", "supplies", "entertainment", "lodging", "transportation", "other"}
    if category not in valid_categories:
        issues.append(f"Unknown expense category: {category}")
        flags.append("invalid_category")
        suggested_actions.append("Select a valid expense category")

    # Incomplete reporting detection: check for essential doc fields
    if not expense.get("date") or not expense.get("total_amount"):
        issues.append("Incomplete reporting: date or total amount missing or unparsed")
        flags.append("incomplete_reporting")
        suggested_actions.append("Provide the transaction date and total amount")

    # High-value expense logic
    if total_amount is not None and total_amount >= policy["high_value_threshold"]:
        # Require justification and at least one receipt and cost center or approver
        justification = (env.get("justification") or expense.get("justification") or "").strip()
        cost_center = env.get("cost_center") or expense.get("cost_center")
        approver = env.get("approver") or expense.get("approver")

        if not justification:
            issues.append("High-value expense requires a justification")
            flags.append("high_value_missing_justification")
            suggested_actions.append("Add a justification explaining the business need")

        if not receipts_present:
            issues.append("High-value expense must include receipts")
            flags.append("high_value_missing_receipt")
            suggested_actions.append("Attach all supporting receipts/documents")

        if not (cost_center or approver):
            issues.append("High-value expense requires cost center or designated approver information")
            flags.append("high_value_missing_approval_info")
            suggested_actions.append("Provide cost center or approver to route for higher approval")

        # If any high-value-specific issues, route for higher approval
        if any(f.startswith("high_value_") or f == "high_value_missing_receipt" for f in flags):
            flags.append("route_for_higher_approval")

    # Routine expense logic: auto-approve travel/lodging under threshold and compliant
    auto_approved = False
    if total_amount is not None and total_amount <= policy["routine_threshold"]:
        # Conditions: receipts present, no category limit violations, category is travel/lodging
        if receipts_present and not any(f in ("lodging_limit_exceeded", "airfare_limit_exceeded", "invalid_category") for f in flags):
            if category in ("lodging", "travel", "transportation"):
                auto_approved = True
                flags.append("auto_approved_routine")

    # Final status determination
    if auto_approved:
        status = "auto_approved"
    # Route for higher approval takes precedence over request for correction
    elif "route_for_higher_approval" in flags or any(f.startswith("lodging_limit_exceeded") or f.startswith("airfare_limit_exceeded") for f in flags):
        status = "requires_higher_approval"
    elif any(f in ("missing_receipt", "incomplete_reporting", "invalid_category") for f in flags):
        status = "needs_correction"
    else:
        status = "approved"

    result = {
        "success": True,
        "status": status,
        "total_amount": total_amount,
        "category": category,
        "issues": issues,
        "flags": flags,
        "suggested_actions": suggested_actions,
        "auto_approved": auto_approved,
        "raw_expense": expense
    }

    # Save to audit log
    try:
        audit_log.save(
            agent_name="Validation Agent",
            result=result,
            user_id=env.get("user_id", expense.get("user_id", "unknown"))
        )
    except Exception:
        # Do not fail on audit logging errors
        pass

    return json.dumps(result, indent=2)


# TODO: Driver that gets called by UI to send query to agentic system
async def get_expense_compliance_response(user_id: str, query: str) -> str:
    """
    Driver that sets up memory and sends a query to the orchestrator agent.

    Parameters:
        user_id (str): The user ID.
        query (str): The user's query to the chatbot.

    Returns:
        str: The model's final response.
    """
    # Logging
    print(f"get_expense_compliance_response() was called. Query: {query[:20]}...")

    # distiller_client = DistillerClient(api_key=API_KEY)

    # # Container for async functions
    # async with distiller_client(
    #     project=PROJECT_NAME,
    #     uuid=user_id,
    #     executor_dict={
    #         #  TODO: update this once other agents are here
            # "Image Understanding Agent": image_understanding_agent,
            # "Critical Thinking Agent": critical_thinking_agent,
            # "Validation Agent": validation_agent
    #     },
    # ) as dc:
        
    #     # Add expense form data to memory
    #     await dc.add_memory(
    #         source="env_variable",
    #         variables_dict=None # TODO: add form data here
    #     )

    #     # Send the query to the agentic system
    #     responses = await dc.query(query=query)
    #     response_list = []
    #     i = 0
    #     async for res in responses:
    #         message = res.get("content", "")
    #         response_list.append(message)
    #         if i % 2 == 0:
    #             print(f"ORCHESTRATOR: ===========================================\n{message}")
    #         else:
    #             print(f"UTILITY AGENT: ==========================================\n{message}")
    #         i += 1

    #     return [response_list[-1]] if len(response_list) > 0 else ""

    return ""