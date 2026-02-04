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
        **CRITICAL ANTI-HALLUCINATION RULES:**
        1. NEVER make up data that is not clearly visible
        2. If you cannot see a field, set it to null
        3. If image is blank/no receipt → ALL fields null
        4. When in doubt → return null

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

        **SELF-CHECK BEFORE RESPONDING:**
        - "Am I making up ANY data?" → If YES: Set to null
        - "Is there a receipt here?" → If NO: All nulls
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
# ========================================== DATA ANALYTICS AGENT ===========================================

async def data_analytics_agent(query: str, env_variable=None, chat_history=None) -> str:
    """
    Analyzes expense data for patterns, trends, anomalies, and insights.
    Leverages historical expense data to provide context and identify unusual patterns.
    
    Parameters:
        query (str): The user's query or analysis instructions.
        env_variable (dict): Environment variables containing validated expense data and history.
        chat_history (list): Previous conversation history.
    
    Returns:
        str: JSON string containing analytics results, insights, and recommendations.
    """
    
    # Extract the validated expense data
    validated_data = env_variable.get("validated_data", {}) if env_variable else {}
    expense_history = env_variable.get("expense_history", []) if env_variable else []
    user_id = env_variable.get("user_id", "unknown") if env_variable else "unknown"
    
    if not validated_data:
        return json.dumps({
            "success": False,
            "error": "No validated expense data provided for analysis",
            "analytics_results": None,
            "insights": [],
            "anomalies": []
        })
    
    # Build the analytics prompt
    analytics_prompt = f"""
You are an expert financial data analyst specializing in expense management and fraud detection.
Your role is to analyze expense submissions for patterns, trends, anomalies, and provide actionable insights.

**CURRENT DATE/TIME:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**CURRENT EXPENSE SUBMISSION:**
{json.dumps(validated_data, indent=2)}

**USER'S HISTORICAL EXPENSE DATA (Last 90 days):**
{json.dumps(expense_history[-50:], indent=2) if expense_history else "No historical data available"}

**USER CONTEXT:**
{query}

**YOUR ANALYSIS TASKS:**

1. **Spending Pattern Analysis:**
   - Compare current expense against user's historical spending patterns
   - Identify if this expense is typical or unusual for this user
   - Analyze spending by category, vendor, time period
   - Calculate average expense amounts by category

2. **Anomaly Detection:**
   - Flag expenses that are statistical outliers (>2 standard deviations from mean)
   - Identify unusual timing (weekend/holiday submissions, late-night transactions)
   - Detect duplicate or near-duplicate expenses
   - Spot suspicious patterns (round numbers, repeated amounts)
   - Check for rapid successive submissions

3. **Trend Identification:**
   - Identify spending trends over time (increasing, decreasing, stable)
   - Spot seasonal patterns or cyclical behavior
   - Detect changes in spending habits
   - Analyze frequency of submissions

4. **Risk Assessment:**
   - Calculate risk score based on multiple factors
   - Identify potential fraud indicators
   - Flag expenses that need extra scrutiny
   - Assess likelihood of policy violations

5. **Comparative Analysis:**
   - Compare against user's own history
   - Identify deviations from normal behavior
   - Calculate percentile ranking of this expense
   - Benchmark against typical ranges

6. **Insight Generation:**
   - Provide actionable insights for approvers
   - Recommend areas for follow-up questions
   - Suggest additional verification steps if needed
   - Offer context to help decision-making

**RISK SCORING FACTORS:**
- Amount deviation from average (weight: 30%)
- Timing anomalies (weight: 15%)
- Vendor/category consistency (weight: 20%)
- Submission frequency (weight: 15%)
- Data quality/completeness (weight: 10%)
- Historical pattern match (weight: 10%)

**OUTPUT FORMAT:**
Return a JSON object with this exact structure:

{{
  "analytics_status": "completed" or "partial" or "failed",
  "analysis_confidence": 0-100,
  
  "expense_profile": {{
    "category": "primary expense category",
    "amount_percentile": 0-100,
    "frequency_assessment": "rare/occasional/frequent/very_frequent",
    "timing_assessment": "normal/unusual/suspicious",
    "vendor_familiarity": "new/occasional/frequent"
  }},
  
  "anomaly_detection": {{
    "is_anomalous": true/false,
    "anomaly_score": 0-100,
    "anomaly_flags": [
      {{
        "type": "amount/timing/duplicate/pattern/other",
        "severity": "LOW/MEDIUM/HIGH/CRITICAL",
        "description": "detailed description of anomaly",
        "evidence": "supporting data or comparison"
      }}
    ]
  }},
  
  "risk_assessment": {{
    "overall_risk_score": 0-100,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "risk_factors": [
      {{
        "factor": "factor name",
        "score": 0-100,
        "weight": "percentage",
        "rationale": "why this is a risk factor"
      }}
    ],
    "fraud_indicators": [
      "list of potential fraud indicators if any"
    ]
  }},
  
  "spending_patterns": {{
    "user_avg_expense_amount": number or null,
    "user_total_expenses_90d": number or null,
    "category_avg_amount": number or null,
    "category_frequency_90d": number or null,
    "deviation_from_average": "percentage or amount",
    "historical_trend": "increasing/decreasing/stable/insufficient_data"
  }},
  
  "comparative_analysis": {{
    "vs_user_average": "higher/lower/similar",
    "vs_category_average": "higher/lower/similar",
    "percentile_rank": 0-100,
    "is_statistical_outlier": true/false,
    "standard_deviations_from_mean": number or null
  }},
  
  "insights": [
    {{
      "insight_type": "pattern/trend/anomaly/recommendation/context",
      "priority": "HIGH/MEDIUM/LOW",
      "message": "actionable insight message",
      "supporting_data": "relevant data points"
    }}
  ],
  
  "recommendations": [
    {{
      "recommendation_type": "approval/verification/investigation/documentation",
      "action": "suggested action to take",
      "reason": "why this recommendation is made",
      "urgency": "immediate/high/medium/low"
    }}
  ],
  
  "verification_suggestions": [
    "Questions or items to verify with the submitter"
  ],
  
  "analysis_summary": {{
    "total_anomalies_detected": 0,
    "critical_anomalies": 0,
    "key_findings": ["summary of key findings"],
    "overall_assessment": "brief overall assessment"
  }},
  
  "metadata": {{
    "historical_data_points": 0,
    "analysis_date": "{datetime.now().isoformat()}",
    "user_id": "{user_id}"
  }}
}}

**CRITICAL RULES:**
1. Be data-driven - base all insights on actual patterns in the data
2. Don't flag normal expenses as anomalous - be reasonable
3. Consider context - business travel expenses are different from office supplies
4. High amounts alone aren't suspicious - context matters
5. Provide actionable insights, not just observations
6. If insufficient historical data, acknowledge this limitation
7. Return ONLY valid JSON, no markdown formatting or extra text
8. Balance thoroughness with practicality

Perform the analysis now.
"""
    
    try:
        # Call the LLM for analytics
        client = AsyncAIRefinery(api_key=API_KEY)
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o",  # Use a capable model for complex analysis
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert financial analyst and fraud detection specialist. You analyze expense data to identify patterns, anomalies, and risks."
                },
                {
                    "role": "user",
                    "content": analytics_prompt
                }
            ],
            temperature=0.2  # Low temperature for consistent analysis
        )
        
        analytics_response = response.choices[0].message.content.strip()
        
        # Parse the analytics response
        try:
            # Clean response of markdown formatting
            clean_response = analytics_response.strip()
            
            # Remove markdown code blocks if present
            import re
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, clean_response)
            
            if match:
                clean_response = match.group(1).strip()
            
            clean_response = clean_response.strip('`').strip()
            
            analytics_result = json.loads(clean_response)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to parse analytics response as JSON: {str(e)}",
                "raw_response": analytics_response,
                "analytics_results": None,
                "insights": [],
                "anomalies": []
            }, indent=2)
        
        # Prepare final result
        result = {
            "success": True,
            "status": analytics_result.get("analytics_status", "completed"),
            "analytics_results": analytics_result,
            "risk_score": analytics_result.get("risk_assessment", {}).get("overall_risk_score", 0),
            "risk_level": analytics_result.get("risk_assessment", {}).get("risk_level", "MEDIUM"),
            "is_anomalous": analytics_result.get("anomaly_detection", {}).get("is_anomalous", False),
            "key_insights": [
                insight.get("message", str(insight))
                for insight in analytics_result.get("insights", [])
            ],
            "recommendations": [
                rec.get("action", str(rec))
                for rec in analytics_result.get("recommendations", [])
            ]
        }
        
        # Save to audit log
        audit_log.save(
            agent_name="Data Analytics Agent",
            result=result,
            user_id=user_id
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Data analytics agent error: {str(e)}",
            "analytics_results": None,
            "insights": [],
            "anomalies": []
        }, indent=2)
    
# ========================================== COMPLIANCE POLICY AGENT ===========================================

async def compliance_policy_agent(query: str, env_variable=None, chat_history=None) -> str:
    """
    Checks expense submissions against organizational policies and compliance rules.
    Determines approval routing, identifies policy violations, and assesses compliance status.
    
    Parameters:
        query (str): The user's query or compliance check instructions.
        env_variable (dict): Environment variables containing validated data, analytics, and policy documents.
        chat_history (list): Previous conversation history.
    
    Returns:
        str: JSON string containing compliance assessment, policy violations, and approval routing.
    """
    
    # Extract data for compliance checking
    validated_data = env_variable.get("validated_data", {}) if env_variable else {}
    analytics_data = env_variable.get("analytics_results", {}) if env_variable else {}
    company_policies = env_variable.get("company_policies", {}) if env_variable else {}
    user_id = env_variable.get("user_id", "unknown") if env_variable else "unknown"
    user_role = env_variable.get("user_role", "employee") if env_variable else "employee"
    user_department = env_variable.get("user_department", "unknown") if env_variable else "unknown"
    
    if not validated_data:
        return json.dumps({
            "success": False,
            "error": "No validated expense data provided for compliance check",
            "compliance_status": "failed",
            "policy_violations": [],
            "approval_required": True
        })
    
    # Default policies if none provided
    if not company_policies:
        company_policies = {
            "daily_meal_limit": 75.00,
            "single_meal_limit": 50.00,
            "lodging_daily_limit": 250.00,
            "domestic_travel_daily_limit": 200.00,
            "international_travel_daily_limit": 300.00,
            "entertainment_requires_justification": True,
            "receipts_required_over": 25.00,
            "alcohol_policy": "allowed_with_clients",
            "approval_thresholds": {
                "manager": 500.00,
                "director": 2500.00,
                "vp": 10000.00,
                "cfo": 25000.00
            },
            "prohibited_categories": ["personal_items", "family_expenses", "gifts_over_50"],
            "mileage_rate": 0.67,
            "international_requires_pre_approval": True
        }
    
    # Build the compliance prompt
    compliance_prompt = f"""
You are an expert compliance officer specializing in corporate expense policy enforcement.
Your role is to thoroughly check expense submissions against company policies and determine appropriate approval routing.

**CURRENT DATE/TIME:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**EMPLOYEE INFORMATION:**
- User ID: {user_id}
- Role: {user_role}
- Department: {user_department}

**EXPENSE SUBMISSION:**
{json.dumps(validated_data, indent=2)}

**ANALYTICS ASSESSMENT:**
{json.dumps(analytics_data, indent=2) if analytics_data else "No analytics available"}

**COMPANY EXPENSE POLICIES:**
{json.dumps(company_policies, indent=2)}

**USER CONTEXT:**
{query}

**YOUR COMPLIANCE TASKS:**

1. **Policy Violation Detection:**
   - Check amount against category-specific limits
   - Verify expense type is allowed under policy
   - Ensure receipts meet documentation requirements
   - Check for prohibited expense categories
   - Validate business purpose requirements
   - Review alcohol/entertainment justifications

2. **Approval Routing Determination:**
   - Determine approval level required based on amount thresholds
   - Identify if escalation is needed
   - Route anomalous expenses for higher review
   - Flag high-risk expenses for additional scrutiny

3. **Documentation Compliance:**
   - Verify required documentation is present
   - Check if additional justification needed
   - Ensure receipt quality meets standards
   - Validate itemization requirements

4. **Special Conditions:**
   - Check pre-approval requirements (international travel, etc.)
   - Identify if expense needs special handling
   - Flag timing-sensitive policy rules
   - Check department-specific policies

5. **Risk-Based Assessment:**
   - Consider analytics risk score in routing
   - Apply stricter checks for high-risk expenses
   - Factor in user's compliance history if available
   - Evaluate contextual factors

**APPROVAL ROUTING LOGIC:**
- Amount < Manager Threshold → Auto-approve if compliant
- Manager Threshold < Amount < Director Threshold → Manager approval
- Director Threshold < Amount < VP Threshold → Director approval
- Amount > VP Threshold → VP or CFO approval
- High Risk Score (>70) → Escalate one level
- Critical Anomalies → Route to Finance/Audit team
- Policy Violations → Reject or route for exception handling

**OUTPUT FORMAT:**
Return a JSON object with this exact structure:

{{
  "compliance_status": "compliant/non_compliant/requires_review/requires_exception",
  "is_compliant": true/false,
  "compliance_score": 0-100,
  
  "policy_violations": [
    {{
      "policy_name": "name of violated policy",
      "severity": "CRITICAL/HIGH/MEDIUM/LOW",
      "violation_description": "detailed description",
      "policy_limit": "what the limit is",
      "actual_value": "what was submitted",
      "recommended_action": "reject/approve_with_exception/request_justification"
    }}
  ],
  
  "policy_warnings": [
    {{
      "policy_name": "name of policy",
      "warning_message": "description of concern",
      "recommendation": "suggested action"
    }}
  ],
  
  "approval_routing": {{
    "approval_required": true/false,
    "approval_level": "auto_approve/manager/director/vp/cfo/ceo",
    "approver_role": "role of person who should approve",
    "routing_reason": "why this approval level",
    "escalation_needed": true/false,
    "escalation_reason": "reason for escalation if applicable",
    "requires_finance_review": true/false,
    "requires_audit_review": true/false
  }},
  
  "documentation_compliance": {{
    "receipt_provided": true/false,
    "receipt_quality": "excellent/good/acceptable/poor/missing",
    "itemization_adequate": true/false,
    "business_purpose_documented": true/false,
    "missing_documentation": ["list of missing docs"],
    "additional_documentation_required": ["list of required docs"]
  }},
  
  "special_conditions": [
    {{
      "condition_type": "pre_approval/exception/special_handling",
      "description": "description of condition",
      "met": true/false,
      "action_required": "what needs to be done"
    }}
  ],
  
  "compliance_checks": [
    {{
      "check_name": "name of compliance check",
      "passed": true/false,
      "details": "details of the check result"
    }}
  ],
  
  "recommendations": [
    {{
      "recommendation": "specific recommendation",
      "priority": "HIGH/MEDIUM/LOW",
      "rationale": "why this is recommended"
    }}
  ],
  
  "required_actions": [
    {{
      "action": "action that must be taken",
      "responsible_party": "who should do it",
      "deadline": "when it should be done or null",
      "blocking": true/false
    }}
  ],
  
  "compliance_summary": {{
    "total_violations": 0,
    "critical_violations": 0,
    "total_warnings": 0,
    "auto_approvable": true/false,
    "requires_manual_review": true/false,
    "overall_assessment": "brief summary",
    "final_recommendation": "approve/reject/request_more_info/route_for_exception"
  }},
  
  "metadata": {{
    "policies_checked": ["list of policies checked"],
    "check_date": "{datetime.now().isoformat()}",
    "user_id": "{user_id}",
    "user_role": "{user_role}"
  }}
}}

**CRITICAL RULES:**
1. Be thorough but fair - don't create obstacles for legitimate expenses
2. Focus on material violations, not technicalities
3. Consider business context and reasonableness
4. Provide clear explanations for any violations
5. Route efficiently - don't over-escalate minor issues
6. Balance policy enforcement with business needs
7. Return ONLY valid JSON, no markdown formatting or extra text
8. If in doubt about a gray area, flag for review rather than auto-reject

Perform the compliance check now.
"""
    
    try:
        # Call the LLM for compliance checking
        client = AsyncAIRefinery(api_key=API_KEY)
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert compliance officer. You enforce expense policies fairly and thoroughly while considering business context."
                },
                {
                    "role": "user",
                    "content": compliance_prompt
                }
            ],
            temperature=0.1  # Very low temperature for consistent policy enforcement
        )
        
        compliance_response = response.choices[0].message.content.strip()
        
        # Parse the compliance response
        try:
            # Clean response of markdown formatting
            clean_response = compliance_response.strip()
            
            # Remove markdown code blocks if present
            import re
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, clean_response)
            
            if match:
                clean_response = match.group(1).strip()
            
            clean_response = clean_response.strip('`').strip()
            
            compliance_result = json.loads(clean_response)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to parse compliance response as JSON: {str(e)}",
                "raw_response": compliance_response,
                "compliance_status": "failed",
                "policy_violations": [],
                "approval_required": True
            }, indent=2)
        
        # Prepare final result
        result = {
            "success": True,
            "status": compliance_result.get("compliance_status", "requires_review"),
            "is_compliant": compliance_result.get("is_compliant", False),
            "compliance_results": compliance_result,
            "violations_count": len(compliance_result.get("policy_violations", [])),
            "critical_violations": sum(
                1 for v in compliance_result.get("policy_violations", [])
                if v.get("severity") == "CRITICAL"
            ),
            "approval_required": compliance_result.get("approval_routing", {}).get("approval_required", True),
            "approval_level": compliance_result.get("approval_routing", {}).get("approval_level", "manager"),
            "final_recommendation": compliance_result.get("compliance_summary", {}).get("final_recommendation", "requires_review")
        }
        
        # Save to audit log
        audit_log.save(
            agent_name="Compliance Policy Agent",
            result=result,
            user_id=user_id
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Compliance policy agent error: {str(e)}",
            "compliance_status": "failed",
            "policy_violations": [],
            "approval_required": True
        }, indent=2)


# ========================================== AUTHOR AGENT ===========================================

async def author_agent(query: str, env_variable=None, chat_history=None) -> str:
    """
    Creates personalized, clear notifications and responses for users based on the
    complete expense processing results. Translates technical outputs into user-friendly messages.
    
    Parameters:
        query (str): The user's original query or notification preferences.
        env_variable (dict): Environment variables containing all processing results.
        chat_history (list): Previous conversation history.
    
    Returns:
        str: JSON string containing formatted notification messages for different channels.
    """
    
    # Extract all the processing results
    validated_data = env_variable.get("validated_data", {}) if env_variable else {}
    analytics_results = env_variable.get("analytics_results", {}) if env_variable else {}
    compliance_results = env_variable.get("compliance_results", {}) if env_variable else {}
    user_id = env_variable.get("user_id", "unknown") if env_variable else "unknown"
    user_name = env_variable.get("user_name", "User") if env_variable else "User"
    notification_preferences = env_variable.get("notification_preferences", {}) if env_variable else {}
    
    if not validated_data:
        return json.dumps({
            "success": False,
            "error": "No expense data provided for notification authoring",
            "messages": {}
        })
    
    # Extract key information for context
    expense_amount = validated_data.get("total_amount", 0)
    vendor_name = validated_data.get("vendor_name", "Unknown Vendor")
    expense_category = validated_data.get("expense_category", "unknown")
    expense_date = validated_data.get("date", "unknown date")
    
    compliance_status = compliance_results.get("status", "unknown") if compliance_results else "unknown"
    approval_required = compliance_results.get("approval_required", True) if compliance_results else True
    approval_level = compliance_results.get("approval_level", "manager") if compliance_results else "manager"
    violations = compliance_results.get("violations_count", 0) if compliance_results else 0
    
    risk_level = analytics_results.get("risk_level", "MEDIUM") if analytics_results else "MEDIUM"
    is_anomalous = analytics_results.get("is_anomalous", False) if analytics_results else False
    
    # Build the authoring prompt
    authoring_prompt = f"""
You are an expert communication specialist who creates clear, professional, and user-friendly notifications
for expense management systems. Your role is to translate technical processing results into messages that
users can easily understand and act upon.

**CURRENT DATE/TIME:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**USER INFORMATION:**
- Name: {user_name}
- User ID: {user_id}

**EXPENSE SUMMARY:**
- Amount: ${expense_amount}
- Vendor: {vendor_name}
- Category: {expense_category}
- Date: {expense_date}

**PROCESSING RESULTS:**

Validation Results:
{json.dumps(validated_data, indent=2)}

Analytics Results:
{json.dumps(analytics_results, indent=2) if analytics_results else "Not available"}

Compliance Results:
{json.dumps(compliance_results, indent=2) if compliance_results else "Not available"}

**USER CONTEXT:**
{query}

**NOTIFICATION PREFERENCES:**
{json.dumps(notification_preferences, indent=2) if notification_preferences else "Use defaults"}

**YOUR TASKS:**

1. **Create Primary Notification:**
   - Clear status update (approved/needs review/rejected/pending)
   - Key information highlighted
   - Next steps clearly stated
   - Professional but friendly tone

2. **Provide Detailed Explanation:**
   - What happened during processing
   - Why the outcome occurred
   - Any issues or concerns identified
   - What the user needs to do next

3. **Tailor for Different Channels:**
   - In-app notification (brief, actionable)
   - Email notification (detailed, professional)
   - SMS/Push notification (very brief, urgent items only)
   - Dashboard status (concise summary)

4. **Handle Different Outcomes:**
   - Approved: Congratulatory, efficient
   - Needs Review: Clear about what's needed, helpful
   - Rejected: Empathetic, constructive, explains why
   - Pending: Reassuring, sets expectations

5. **User-Friendly Language:**
   - Avoid technical jargon
   - Explain policy terms simply
   - Be specific about actions needed
   - Use positive, helpful tone

**TONE GUIDELINES:**
- Professional but approachable
- Clear and concise
- Empathetic when delivering bad news
- Action-oriented
- Respectful of user's time

**OUTPUT FORMAT:**
Return a JSON object with this exact structure:

{{
  "authoring_status": "completed" or "failed",
  "notification_type": "approval/rejection/review_needed/pending/error",
  
  "messages": {{
    "in_app": {{
      "title": "Brief notification title",
      "body": "Main notification message (2-3 sentences)",
      "action_button": "text for primary action button",
      "action_url": "URL or route for action",
      "priority": "high/medium/low"
    }},
    
    "email": {{
      "subject": "Email subject line",
      "greeting": "Personalized greeting",
      "body": "Full email body with details (multiple paragraphs)",
      "key_points": ["bullet points of key information"],
      "next_steps": ["clear action items for the user"],
      "closing": "Email closing",
      "signature": "System signature"
    }},
    
    "sms": {{
      "message": "Very brief SMS message (under 160 chars)",
      "send_condition": "only_if_urgent/always/user_preference"
    }},
    
    "push": {{
      "title": "Push notification title",
      "body": "Push notification body (1 sentence)",
      "send_condition": "only_if_urgent/always/user_preference"
    }},
    
    "dashboard": {{
      "status_badge": "approved/rejected/pending/review",
      "status_color": "green/red/yellow/blue",
      "summary": "One sentence summary",
      "details": "Additional details for dashboard view"
    }}
  }},
  
  "key_information": {{
    "expense_id": "generated or existing ID",
    "status": "final status",
    "amount": {expense_amount},
    "submitted_date": "{datetime.now().isoformat()}",
    "expected_processing_time": "time estimate if pending",
    "approval_timeline": "when decision expected"
  }},
  
  "user_actions": [
    {{
      "action": "what the user should do",
      "priority": "required/recommended/optional",
      "deadline": "when to do it or null",
      "instructions": "how to do it"
    }}
  ],
  
  "helpful_tips": [
    "Tips for future submissions or current issue"
  ],
  
  "support_info": {{
    "contact_available": true/false,
    "contact_method": "email/phone/chat",
    "faq_link": "URL to FAQs or null",
    "escalation_available": true/false
  }},
  
  "metadata": {{
    "template_used": "name of message template",
    "personalization_applied": true/false,
    "language": "en",
    "generated_at": "{datetime.now().isoformat()}"
  }}
}}

**CRITICAL RULES:**
1. Be clear and direct - users should immediately understand the status
2. Always include next steps - users should know what to do
3. Be empathetic with rejections - explain constructively
4. Celebrate approvals - make users feel good about compliant submissions
5. Set realistic expectations for pending items
6. Use the user's name to personalize
7. Return ONLY valid JSON, no markdown formatting or extra text
8. Make messages actionable - every notification should have a purpose

**SPECIFIC SCENARIOS TO HANDLE:**

If APPROVED:
- Congratulate the user
- Confirm the amount and details
- Explain when reimbursement will occur
- Encourage continued compliance

If REJECTED:
- Start with empathy
- Clearly explain the reason
- Provide specific steps to resubmit correctly
- Offer to help if needed

If NEEDS REVIEW:
- Explain what's being reviewed
- Set timeline expectations
- List what user can do to expedite
- Reassure them it's in progress

If PENDING APPROVAL:
- Confirm receipt
- Explain the approval process
- Set timeline expectations
- No action needed from user

Generate the notifications now.
"""
    
    try:
        # Call the LLM for message authoring
        client = AsyncAIRefinery(api_key=API_KEY)
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert communication specialist. You create clear, user-friendly notifications that help people understand and act on expense processing results."
                },
                {
                    "role": "user",
                    "content": authoring_prompt
                }
            ],
            temperature=0.3  # Some creativity for natural language
        )
        
        authoring_response = response.choices[0].message.content.strip()
        
        # Parse the authoring response
        try:
            # Clean response of markdown formatting
            clean_response = authoring_response.strip()
            
            # Remove markdown code blocks if present
            import re
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, clean_response)
            
            if match:
                clean_response = match.group(1).strip()
            
            clean_response = clean_response.strip('`').strip()
            
            authoring_result = json.loads(clean_response)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to parse authoring response as JSON: {str(e)}",
                "raw_response": authoring_response,
                "messages": {}
            }, indent=2)
        
        # Prepare final result
        result = {
            "success": True,
            "status": authoring_result.get("authoring_status", "completed"),
            "notification_type": authoring_result.get("notification_type", "pending"),
            "messages": authoring_result.get("messages", {}),
            "user_actions": authoring_result.get("user_actions", []),
            "key_information": authoring_result.get("key_information", {})
        }
        
        # Save to audit log
        audit_log.save(
            agent_name="Author Agent",
            result=result,
            user_id=user_id
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Author agent error: {str(e)}",
            "messages": {}
        }, indent=2)

#=========================================== END AGENTS ================================================

# #=========================================== TESTING FUNCTION ===========================================
# async def test_agents():
#     """
#     Test function to demonstrate the agents working together.
#     """
    
#     # Sample validated expense data
#     sample_validated_data = {
#         "vendor_name": "The Capital Grille",
#         "date": "2026-02-03",
#         "total_amount": 187.50,
#         "tax_amount": 15.00,
#         "tip_amount": 35.00,
#         "subtotal": 137.50,
#         "currency": "USD",
#         "expense_category": "meals",
#         "payment_method": "credit",
#         "confidence_score": 95
#     }
    
#     # Sample historical data
#     sample_history = [
#         {"date": "2026-01-15", "amount": 45.00, "category": "meals"},
#         {"date": "2026-01-22", "amount": 32.50, "category": "meals"},
#         {"date": "2026-01-28", "amount": 67.00, "category": "meals"}
#     ]
    
#     # Test Data Analytics Agent
#     print("=" * 80)
#     print("TESTING DATA ANALYTICS AGENT")
#     print("=" * 80)
    
#     analytics_result = await data_analytics_agent(
#         query="Analyze this expense submission for patterns and anomalies",
#         env_variable={
#             "validated_data": sample_validated_data,
#             "expense_history": sample_history,
#             "user_id": "test_user_123"
#         }
#     )
#     print(analytics_result)
    
#     # Test Compliance Policy Agent
#     print("\n" + "=" * 80)
#     print("TESTING COMPLIANCE POLICY AGENT")
#     print("=" * 80)
    
#     compliance_result = await compliance_policy_agent(
#         query="Check this expense against company policies",
#         env_variable={
#             "validated_data": sample_validated_data,
#             "analytics_results": json.loads(analytics_result).get("analytics_results"),
#             "user_id": "test_user_123",
#             "user_role": "senior_engineer",
#             "user_department": "engineering"
#         }
#     )
#     print(compliance_result)
    
#     # Test Author Agent
#     print("\n" + "=" * 80)
#     print("TESTING AUTHOR AGENT")
#     print("=" * 80)
    
#     author_result = await author_agent(
#         query="Create notification for the user about their expense submission",
#         env_variable={
#             "validated_data": sample_validated_data,
#             "analytics_results": json.loads(analytics_result).get("analytics_results"),
#             "compliance_results": json.loads(compliance_result).get("compliance_results"),
#             "user_id": "test_user_123",
#             "user_name": "John Smith"
#         }
#     )
#     print(author_result)


# # Run tests if executed directly
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(test_agents())


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