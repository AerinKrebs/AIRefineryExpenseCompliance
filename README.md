# AIRefineryExpenseCompliance

## How to Run

1. Clone this repo

2. Create a file called `.env` and put the following line in:
```plaintext
API_KEY="<YOUR API KEY HERE>"
```
3. Activate the venv
4. pip install the requiremnts.txt

5. In the terminal, run this command:
```bash
streamlit run expense_compliance_app.py
```

## File Structure
* ```NortTwinExample```: directory with the North Twin chatbot.
* ```tests```: directory with unit tests and data to run tests.
* ```agents.py```:  contains python code for AI agents.
* ```create_air_project.py```:  creates a new project or version of a project in AI Refinery (needs to be run when changes are made to config or agents(?)).
* ```expense_compliance_app.py```:  contains Streamlit UI for the project.

## Testing For Devs
* Image Agent : move test_image_agent.py to the root and one of the test files invoice.png or receipt.jpg. Run 'python test_local_receipt.py receipt.jpg'

* Validation Agent :  move test_validation_agent.py to the root and run 'python test_validation_agent.py'

## Contributors
* xxx MM/dd/YYYY