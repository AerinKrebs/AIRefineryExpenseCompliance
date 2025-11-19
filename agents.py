import os
import yaml
import pandas as pd
from air import AsyncAIRefinery, DistillerClient
from dotenv import load_dotenv

# TODO: Load API Key & set other state variables
# API_KEY = 
# PROJECT_NAME = 

# TODO: Helper function that sends a prompt to a model hosted on AIR

# TODO: Functions that build agent prompts and give proper context/tools

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
    #         "<Agent Name>": agent_function_name,
    #     },
    # ) as dc:
        
    #     # Add Cosmic Mart data to memory
    #     await dc.add_memory(
    #         source="env_variable",
    #         variables_dict=cosmic_mart_data
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