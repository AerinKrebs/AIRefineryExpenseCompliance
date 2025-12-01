import os
import yaml
import pandas as pd
from air import AsyncAIRefinery, DistillerClient
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


# ========================================== AGENTS ===========================================

# TODO: Function for image understanding agent
async def image_understanding_agent(query: str, env_variable=None, chat_history=None) -> str:
    return ""

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