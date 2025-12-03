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
    return response.choices[0].message.content.strip()

#=========================================== SUPPORTING FUNCTIONS ===========================================
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
    return response.choices[0].message.content.strip()
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
        
        # Parse response - handle markdown code blocks
        try:
            clean_response = response.strip()
            
            # ==================== FIXED PARSING LOGIC ====================
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
        
        # Add metadata
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
            user_id=env_variable.get("user_id", "unknown")
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

# TODO: Function for validation agent
async def validation_agent(query: str, env_variable=None, chat_history=None) -> str:
    return ""


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