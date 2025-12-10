import os
import yaml
import json
import pandas as pd
from air import AsyncAIRefinery, DistillerClient
from audit import audit_log
from dotenv import load_dotenv
from datetime import datetime

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

# Validation Agent: ensures submitted expenses comply with org policies
# ========================================== VALIDATION AGENT ===========================================

async def validation_agent(query: str, env_variable=None, chat_history=None) -> str:
    """
    Agentic validator that uses an LLM to intelligently validate extracted expense data
    for correctness, consistency, and data quality. Does NOT perform policy checks.
    
    Parameters:
        query (str): The user's query or validation instructions.
        env_variable (dict): Environment variables containing extracted expense data.
        chat_history (list): Previous conversation history.
    
    Returns:
        str: JSON string containing validation results and corrected data.
    """
    
    # Extract the data to validate
    extracted_data = env_variable.get("extracted_data", {}) if env_variable else {}
    
    if not extracted_data:
        return json.dumps({
            "success": False,
            "error": "No data provided for validation",
            "validated_data": None,
            "validation_errors": ["Missing input data"],
            "validation_warnings": []
        })
    
    # Build the validation prompt for the LLM
    validation_prompt = f"""
You are an expert data validator for expense management systems. Your job is to validate extracted receipt/invoice data for accuracy, consistency, and data quality ONLY. 

**IMPORTANT: DO NOT perform any policy checks, approval routing, or compliance assessments. Another agent will handle those.**


**CURRENT DATE/TIME:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**CURRENT DATE (for validation):** {datetime.now().strftime("%Y-%m-%d")}

**DATA TO VALIDATE:**
{json.dumps(extracted_data, indent=2)}

**USER CONTEXT:**
{query}

**YOUR VALIDATION TASKS:**

1. **Field Completeness Check:**
   - Verify all critical fields are present: vendor_name, date, total_amount
   - Check for missing optional fields that should be present based on the raw text
   - Flag any suspicious null values

2. **Data Type & Format Validation:**
   - Ensure dates are in YYYY-MM-DD format and are valid dates
   - **CRITICAL: Check that dates are NOT in the future (after {datetime.now().strftime("%Y-%m-%d")})**
   - Ensure times are in HH:MM format if present
   - Verify all monetary values are valid numbers (not negative, no extreme outliers)
   - Check currency codes are valid ISO codes (USD, EUR, GBP, etc.)
   - Validate card_last_four is exactly 4 digits if present

3. **Business Logic Validation:**
   - Verify: subtotal + tax_amount + tip_amount = total_amount (allow 1% tolerance for rounding)
   - **CRITICAL: Check that total_amount is correct**
   - Verify: sum of line_items totals = subtotal (allow small rounding differences)
   - For each line item: verify quantity × unit_price = total
    - Check if dates are reasonable (not in future, not too old like >10 years from {datetime.now().strftime("%Y-%m-%d")})

4. **Consistency Checks:**
   - Compare extracted values against raw_text_extracted to verify accuracy
   - Check if vendor name matches what's in the raw text
   - Verify amounts mentioned in raw text match extracted amounts
   - Ensure expense_category makes sense for the vendor and line items

5. **Data Quality Assessment:**
   - Evaluate if confidence_score aligns with data quality
   - Identify any discrepancies or suspicious values
   - Flag potential OCR errors or misreadings

**CORRECTION INSTRUCTIONS:**
- If you find errors, provide corrected values when possible
- Use the raw_text_extracted to help correct misreadings
- Apply reasonable defaults only when safe (e.g., USD for currency if $ symbol seen)
- Do NOT guess or make up data that isn't in the raw text

**STATUS GUIDELINES:**
- Use "approved" if all data is valid and complete
- Use "needs_correction" if there are data quality issues that need fixing
- Use "incomplete_data" if critical fields are missing
- DO NOT use policy-related statuses like "requires_higher_approval" or "route_for_higher_approval"

**OUTPUT FORMAT:**
Return a JSON object with this exact structure:

{{
  "validation_status": "approved" or "needs_correction" or "incomplete_data",
  "is_valid": true/false,
  "data_quality_score": 0-100,
  
  "validation_errors": [
    {{
      "field": "field_name",
      "issue": "description of error",
      "severity": "CRITICAL/HIGH/MEDIUM/LOW",
      "current_value": "what was found",
      "expected": "what it should be or validation rule"
    }}
  ],
  
  "validation_warnings": [
    {{
      "field": "field_name",
      "issue": "description of warning",
      "recommendation": "suggested action"
    }}
  ],
  
  "corrected_data": {{
    // Full corrected version of the input data with fixes applied
    // Include ALL fields from original, even if unchanged
  }},
  
  "corrections_made": [
    {{
      "field": "field_name",
      "original_value": "old value",
      "corrected_value": "new value",
      "reason": "why correction was made"
    }}
  ],
  
  "validation_summary": {{
    "total_errors": 0,
    "critical_errors": 0,
    "total_warnings": 0,
    "fields_corrected": 0,
    "data_completeness_score": 0-100,
    "calculation_accuracy": "VERIFIED/FAILED/PARTIAL"
  }},
  
  "data_quality_notes": [
    "Any data quality concerns or observations",
    "OCR errors or potential misreadings",
    "Recommendations for data improvement"
  ]
}}

**CRITICAL RULES:**
1. ONLY validate data quality - do NOT check policies, amounts limits, approval requirements
2. Be thorough but fair - don't flag minor issues as critical
3. Base corrections on actual evidence from raw_text_extracted
4. If calculations don't match, identify which field is likely wrong
5. Consider OCR errors (0/O, 1/I, 5/S confusion)
6. Return ONLY valid JSON, no markdown formatting or extra text
7. Focus on: completeness, accuracy, format, consistency - NOT policy compliance

Perform the validation now.
"""
    
    try:
        # Call the LLM for validation
        client = AsyncAIRefinery(api_key=API_KEY)
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o",  # Use a capable model for reasoning
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert data validator. You validate financial data for accuracy and quality. You do NOT perform policy checks or compliance assessments."
                },
                {
                    "role": "user",
                    "content": validation_prompt
                }
            ],
            temperature=0.1  # Low temperature for consistent validation
        )
        
        validation_response = response.choices[0].message.content.strip()
        
        # Parse the validation response
        try:
            # Clean response of markdown formatting
            clean_response = validation_response.strip()
            
            # Remove markdown code blocks if present
            import re
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, clean_response)
            
            if match:
                clean_response = match.group(1).strip()
            
            # Remove any leading/trailing ``` markers
            clean_response = clean_response.strip('`').strip()
            
            validation_result = json.loads(clean_response)
            
            # Ensure required top-level fields exist
            validation_result.setdefault("validation_status", "needs_correction")
            validation_result.setdefault("is_valid", False)
            validation_result.setdefault("validation_errors", [])
            validation_result.setdefault("validation_warnings", [])
            validation_result.setdefault("corrected_data", extracted_data)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to parse validation response as JSON: {str(e)}",
                "raw_response": validation_response,
                "validated_data": None,
                "validation_errors": ["LLM returned invalid JSON format"],
                "validation_warnings": []
            }, indent=2)
        
        # Prepare final result
        result = {
            "success": validation_result.get("is_valid", False),
            "status": validation_result.get("validation_status"),
            "validated_data": validation_result.get("corrected_data"),
            "validation_errors": [
                err.get("issue", str(err)) if isinstance(err, dict) else str(err)
                for err in validation_result.get("validation_errors", [])
            ],
            "validation_warnings": [
                warn.get("issue", str(warn)) if isinstance(warn, dict) else str(warn)
                for warn in validation_result.get("validation_warnings", [])
            ],
            "validation_details": validation_result,  # Full detailed response
            "data_quality": {
                "score": validation_result.get("data_quality_score", 0),
                "summary": validation_result.get("validation_summary", {})
            }
        }
        
        # Save to audit log
        audit_log.save(
            agent_name="Validation Agent",
            result=result,
            user_id=env_variable.get("user_id", "unknown")
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Validation agent error: {str(e)}",
            "validated_data": None,
            "validation_errors": [str(e)],
            "validation_warnings": []
        }, indent=2)
#=========================================== END AGENTS ================================================
#=========================================== DRIVER FUNCTION ===========================================

# Driver that gets called by UI to send query to agentic system
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

    #this is a placeholder for future implementation of the orchestrator if memory is not working
    # distiller_client = DistillerClient(api_key=API_KEY)

    # # Container for async functions
    # async with distiller_client(
    #     project=PROJECT_NAME,
    #     uuid=user_id,
    #     executor_dict={
            # "Image Understanding Agent": image_understanding_agent,
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