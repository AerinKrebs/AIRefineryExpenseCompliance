import os
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime, date
from agents import *
from air import DistillerClient
from dotenv import load_dotenv

# Load API key from .env
load_dotenv() 
API_KEY = str(os.getenv("API_KEY"))
USER_ID = ""  # TODO

# ==================================== STREAMLIT APP LOGIC ====================================

# Page configuration
if "visibility" not in st.session_state:
    st.session_state.visibility = "visible"
    st.session_state.disabled = False

st.set_page_config(
    page_title="Expense Compliance Assistant",
    layout="wide"
)

st.title("Expense Compliance Assistant")
st.markdown("---")

# Split layout into chat and form
col1, col2 = st.columns(2, gap="large")

# ==================================== CHAT ASSISTANT (LEFT COLUMN) ====================================

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    
    # Welcome message
    welcome_msg = "Hi there! I'm your expense compliance assistant. How can I help you today?"
    
    # Add message to chat
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

with col1:
    st.header("Compliance Chat Assistant")
    
    # Create a container for chat messages with fixed height
    chat_container = st.container(height=500)
    
    with chat_container:
        # Render messages on rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Take user messages
    if prompt := st.chat_input("What expense questions do you have today?"):
        
        # Add user message to the page
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Get the agentic response
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Finding the best results for your query..."):
                    response = asyncio.run(get_expense_compliance_response(USER_ID, prompt))
                    
                    # TODO: comment back in
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # TODO: comment out - echo's user's message
                    # call driver function to get response and render the message
                    temp_message = f"YOUR QUERY WAS: {prompt}"
                    st.markdown(temp_message)
                    st.session_state.messages.append({"role": "assistant", "content": temp_message})
        
        st.rerun()
    
    # Chat tips
    with st.expander("Ask me about..."):
        st.markdown("""
        - Expense policy questions
        - Category guidelines
        - Reimbursement rules
        - Receipt requirements
        - Approval workflows
        - Spending limits
        """)

# ==================================== EXPENSE FORM (RIGHT COLUMN) ====================================

with col2:
    st.header("Expense Report Form")
    
    # Create the form
    with st.form("expense_form"):
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Employee Information
            st.markdown("#### Employee Information")
            employee_name = st.text_input("Employee Name*", placeholder="John Doe")
            employee_id = st.text_input("Employee ID", placeholder="EMP001")
            department = st.selectbox("Department*", 
                                      ["Select Department", "Sales", "Marketing", "Engineering", 
                                       "HR", "Finance", "Operations", "IT", "Other"])
            
            # Expense Details
            st.markdown("#### Expense Information")
            expense_date = st.date_input("Expense Date*", value=date.today())
            expense_amount = st.number_input("Amount ($)*", min_value=0.0, step=0.01, format="%.2f")
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "Other"])
            
        with col_b:
            # Category and Type
            st.markdown("#### Expense Category")
            category = st.selectbox("Category*", 
                                   ["Select Category", "Travel", "Meals & Entertainment", 
                                    "Office Supplies", "Software/Subscriptions", "Training", 
                                    "Client Entertainment", "Transportation", "Accommodation", 
                                    "Other"])
            
            payment_method = st.selectbox("Payment Method*",
                                         ["Select Method", "Company Card", "Personal Card", 
                                          "Cash", "Bank Transfer"])
            
            project_code = st.text_input("Project/Cost Center Code", placeholder="PRJ-2024-001")
            
            # Receipt Upload
            st.markdown("#### Receipt Attachment")
            receipt_file = st.file_uploader("Upload Receipt (PDF/Image)*", 
                                           type=["pdf", "png", "jpg", "jpeg"],
                                           help="Upload a clear photo or PDF of your receipt")
        
        # Full width fields
        st.markdown("#### Additional Details")
        merchant_name = st.text_input("Merchant/Vendor Name", placeholder="Restaurant ABC, Hotel XYZ, etc.")
        
        business_purpose = st.text_area("Business Purpose/Description*", 
                                       placeholder="Describe the business purpose of this expense...",
                                       height=80)
        
        col_c, col_d = st.columns(2)
        with col_c:
            attendees = st.text_input("Attendees (if applicable)", 
                                     placeholder="Names of people present")
        with col_d:
            reimbursable = st.checkbox("Reimbursable", value=True)
        
        notes = st.text_area("Additional Notes", 
                            placeholder="Any additional information or context...",
                            height=60)
        
        st.markdown("---")
        
        # Submit button
        submitted = st.form_submit_button("Submit Expense Report", use_container_width=True, type="primary")
    
    # Handle form submission
    if submitted:
        # Validation
        errors = []
        if not employee_name:
            errors.append("Employee Name is required")
        if department == "Select Department":
            errors.append("Department is required")
        if expense_amount <= 0:
            errors.append("Expense amount must be greater than 0")
        if category == "Select Category":
            errors.append("Category is required")
        if payment_method == "Select Method":
            errors.append("Payment Method is required")
        if not business_purpose:
            errors.append("Business Purpose is required")
        if not receipt_file:
            errors.append("Receipt attachment is required")
        
        if errors:
            st.error("Please fix the following errors:")
            for error in errors:
                st.error(f"• {error}")
        else:
            # Success message
            st.success("Expense report submitted successfully!")
            
            # Display summary
            st.markdown("### Submission Summary")
            
            summary_data = {
                "Field": ["Employee Name", "Employee ID", "Department", "Expense Date", 
                         "Amount", "Currency", "Category", "Payment Method", "Merchant", 
                         "Business Purpose", "Reimbursable"],
                "Value": [employee_name, employee_id or "N/A", department, 
                         expense_date.strftime("%B %d, %Y"), f"${expense_amount:,.2f}", 
                         currency, category, payment_method, merchant_name or "N/A", 
                         business_purpose, "Yes" if reimbursable else "No"]
            }
            
            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if receipt_file:
                st.info(f"📎 Receipt attached: {receipt_file.name} ({receipt_file.size / 1024:.1f} KB)")
            
            st.balloons()

# ==================================== SIDEBAR ====================================

with st.sidebar:
    st.header("Instructions")
    st.markdown("""
    **How to use this tool:**
    
    1. **Chat with the assistant** (left) to ask questions about expense policies and compliance
    
    2. **Fill out the expense form** (right) with all required information
    
    3. **Upload your receipt** as PDF or image
    
    4. **Submit** when ready
    """)
    
    st.markdown("---")
    
    st.markdown("**Required Fields (*):**")
    st.markdown("""
    - Employee Name
    - Department
    - Expense Date
    - Amount
    - Category
    - Payment Method
    - Business Purpose
    - Receipt Attachment
    """)
    
    st.markdown("---")
    
    st.markdown("**Tips:**")
    st.markdown("""
    - Ensure receipts are clear and legible
    - Provide detailed business purpose
    - Submit expenses within 30 days
    - Keep original receipts for records
    """)
    
    st.markdown("---")
    st.markdown("**Need Help?**")
    st.markdown("expenses@company.com")
    st.markdown("(555) 123-4567")