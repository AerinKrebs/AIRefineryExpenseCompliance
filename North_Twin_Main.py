import asyncio
import os
import pandas as pd
import streamlit as st
from air import AsyncAIRefinery, DistillerClient
from dotenv import load_dotenv
import yaml

# ------------------- SETUP -------------------
load_dotenv()
api_key = str(os.getenv("API_KEY"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_CSV = os.path.join(BASE_DIR, "profile.csv")
TRANSACTIONS_CSV = os.path.join(BASE_DIR, "transactions.csv")


def try_parse_yaml(possible_yaml):
    if not isinstance(possible_yaml, str):
        return possible_yaml
    try:
        parsed = yaml.safe_load(possible_yaml)
        return parsed if parsed is not None else possible_yaml
    except yaml.YAMLError:
        return possible_yaml


# ------------------- AGENT HELPERS -------------------
async def run_agent(prompt: str):
    """Helper to send prompt to LLM"""
    client = AsyncAIRefinery(api_key=api_key)
    response = await client.chat.completions.create(
        model="meta-llama/Llama-3.1-70B-Instruct",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ------------------- AGENT FUNCTIONS -------------------
async def digital_twin_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    prompt = f"""
You are a financial memory loader. Summarize and confirm how many items are loaded into memory.

Financial Profile:
{env_variable.get('financial_profile') if isinstance(env_variable, dict) else env_variable}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def categorizer_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    prompt = f"""
You are a transaction categorization assistant. Categorize each transaction and summarize totals.

Transactions:
{env_variable.get('transactions') if isinstance(env_variable, dict) else env_variable}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def pattern_analyser_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    categorized_text = env_variable.get('categorizer_agent') if isinstance(env_variable, dict) else env_variable
    prompt = f"""
You are a financial behavior analyst. Analyze the categorized transactions and summary to detect spending patterns without recommendations.

Categorized Transactions:
{categorized_text}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def nudge_generator_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    prompt = f"""
You are a smart nudge assistant. Mainly Based on the user's spending patterns, suggest one actionable behavioral nudge to improve their finances.

Spending Pattern:
{env_variable.get('pattern_analyser_agent') if isinstance(env_variable, dict) else env_variable}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def options_generator_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    prompt = f"""
You are a financial scenario planner. Given the profile, nudge and user goal, generate 2 options for the user to consider (e.g. increase monthly payment by 50%, pay one sum amount, etc.).

Context:
{env_variable}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def options_simulator_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    scenarios = env_variable.get('options_generator_agent') if isinstance(env_variable, dict) else env_variable
    profile = env_variable.get('financial_profile') if isinstance(env_variable, dict) else None
    prompt = f"""
You are a simulation engine. Simulate outcomes of the user’s options using their profile.

Scenarios:
{scenarios}
Profile:
{profile}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def goal_tracker_agent(query, env_variable=None, chat_history=None):
    user_goal = env_variable.get('user_goal') if isinstance(env_variable, dict) else env_variable
    prompt = f"""
You are a financial goal tracker. The user has a goal (e.g., repay debt, build savings). Break the goal to track progress and store it for future without any simulation or predicitions.

Goal Context:
{user_goal}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


async def narrative_generator_agent(query, env_variable=None, chat_history=None):
    env_variable = try_parse_yaml(env_variable)
    prompt = f"""
You are a narrative assistant. Your job is to generate a personalized financial scenario summary using the user’s financial data. The tone should be supportive and conversational, and it must follow this exact format:

---
{{Emma}}, you mentioned your goal: "{{user_goal}}". Based on your financial profile, we've simulated the following personalized strategies to help you achieve that. Here's what we found:

💼 Quick Financial Snapshot  
{{financial_snapshot_table}}

Ⓐ {{a_scenario_headline}}  
{{a_consequence_of_the_scenario}}
{{a_consequence_of_the_scenario}} 
{{a_additional_details}}
{{a_additional_tips_based_on_user_spending}} 

Simulation Preview:  
{{option_a_simulation_table}}

Ⓑ {{propose_b_scenario_headline}}  
{{b_consequence_of_the_scenario}} 
{{b_consequence_of_the_scenario}}  
{{b_additional_details}} 
{{b_additional_tips_based_on_user_spending}} 
Simulation Preview:  
{{option_b_simulation_table}}

📌 Your Current Plan (for reference only)  
{{current_plan_summary}}  
Simulation Preview:  
{{current_plan_simulation_table}}

🗣️ What would you like to do next, {{Emma}}?  
Respond with:  
✅ "Choose A" – {{a_scenario_headline}}  
✅ "Choose B" – {{b_scenario_headline}}
💬 "Help me decide" – I can guide you further

---
Use the following context to extract all necessary values:

Context:
{env_variable}

Query:
{query}

Chat History:  
{chat_history}

"""
    return await run_agent(prompt)


executor_dict = {
    "Digital Twin Agent": digital_twin_agent,
    "Categorizer Agent": categorizer_agent,
    "Pattern Analyser Agent": pattern_analyser_agent,
    "Nudge Generator Agent": nudge_generator_agent,
    "Options Generator Agent": options_generator_agent,
    "Options Simulator Agent": options_simulator_agent,
    "Goal Tracker Agent": goal_tracker_agent,
    "Narrative Generator Agent": narrative_generator_agent,
}


# ------------------- LOAD CSV DATA -------------------
try:
    profile_df = pd.read_csv(PROFILE_CSV)
    profile_data = {row["Item"]: row["Amount"] for _, row in profile_df.iterrows()}
    #st.write("Loaded Profile data")
except FileNotFoundError:
    profile_data = {}
    st.error("⚠️ profile.csv not found!")


try:
    transactions_df = pd.read_csv(TRANSACTIONS_CSV)
    transactions_data = transactions_df.to_dict(orient="records")
    #st.write("Loaded transactions data")
except FileNotFoundError:
    transactions_data = []
    st.error("⚠️ transactions.csv not found!")


## ------------------- STREAMLIT UI -------------------
st.set_page_config(page_title="North Twin - Digital Financial Advisor", layout="wide")
st.title("💰 North Twin – Your Digital Financial Advisor")
#st.write("Type your financial goal or question below to chat with North Twin.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi Emma! 👋 I am North Twin, your digital financial advisor. How can I help today?"}
    ]

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle user input
if user_input := st.chat_input("Ask North Twin a question..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    async def distiller_north_twin():
        distiller_client = DistillerClient(api_key=api_key)

        async with distiller_client(
            project="NorthTwin_AIRefinery_Challenge_Project_Sep2025",
            uuid="emma_user",  # unique per app/user
            executor_dict=executor_dict
        ) as dc:

            # Add profile and transactions to memory
            await dc.add_memory(
                source="env_variable",
                variables_dict={
                    "financial_profile": profile_data,
                    "transactions": transactions_data,
                    "user_goal": user_input,
                }
            )
            st.write("✅ Financial profile and transactions loaded into memory.")

            # Query the Distiller agent
            responses = await dc.query(query=user_input)
            async for response in responses:
                narrative_output = response.get("content", "")
                st.markdown(narrative_output)
                st.session_state.messages.append({"role": "assistant", "content": narrative_output})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your financial data..."):
            asyncio.run(distiller_north_twin())