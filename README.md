# AIRefineryExpenseCompliance

## How to Run

1. Clone this repo

2. Create a file called `.env` and put the following line in:
```plaintext
API_KEY="<YOUR API KEY HERE>"
```

3. Activate the venv: Optional at this time
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install the requirements:
```bash
pip install -r requirements.txt
```

5. In the terminal, run this command:
```bash
streamlit run expense_compliance_app.py
```

## File Structure

```
AIRefineryExpenseCompliance/
├── NorthTwinExample/          # Directory with the North Twin chatbot example
├── tests/                     # Directory with unit tests and test data
│   ├── debug_validation.py    # Debug script for validation testing
│   ├── invoice.png            # Sample invoice image for testing
│   ├── receipt.jpg            # Sample receipt image for testing
│   ├── test_image_agent.py    # Unit tests for image processing agent
│   ├── test_local_receipt.py  # Local testing script for receipt processing
│   └── test_validation_agent.py # Unit tests for validation agent
├── venv/                      # Python virtual environment
├── .env                       # Environment variables (API keys) - not in repo
├── .gitignore                 # Git ignore configuration
├── agents.py                  # Core AI agent implementations
├── audit.py                   # Audit functionality
├── audit_log.json             # JSON log file for audit trails
├── config.yaml                # Project configuration file
├── create_air_project.py      # Script to create/update AI Refinery project
├── expense_compliance_app.py  # Main Streamlit UI application
├── package-lock.json          # NPM package lock file
├── README.md                  # Project documentation (this file)
└── requirements.txt           # Python package dependencies
```

### Key Files Description

* **`NorthTwinExample/`**: Example implementation directory containing the North Twin chatbot reference code.

* **`tests/`**: Contains all unit tests and sample data files for testing agents.
  * `debug_validation.py` - Debugging utilities for validation agent
  * `invoice.png`, `receipt.jpg` - Sample images for testing
  * `test_image_agent.py` - Tests for image extraction functionality
  * `test_local_receipt.py` - Local receipt processing tests
  * `test_validation_agent.py` - Tests for expense validation logic

* **`agents.py`**: Core Python module containing AI agent implementations for expense processing and validation.

* **`audit.py`**: Handles audit logging and compliance tracking functionality.

* **`audit_log.json`**: JSON-formatted log file storing audit trail data.

* **`config.yaml`**: YAML configuration file for AI Refinery project settings and agent parameters.

* **`create_air_project.py`**: Script to create a new project or update an existing version in AI Refinery. Run this when changes are made to config or agents.

* **`expense_compliance_app.py`**: Main Streamlit application providing the user interface for expense compliance checking.

* **`requirements.txt`**: Lists all Python package dependencies required for the project.

* **`.env`**: Environment configuration file (not tracked in git) containing API keys and sensitive credentials.

## Testing For Devs

### Image Agent Testing
Move `test_image_agent.py` to the root along with one of the test files (`invoice.png` or `receipt.jpg`). Run:
```bash
python test_local_receipt.py receipt.jpg
```

### Validation Agent Testing
Move `test_validation_agent.py` to the root and run:
```bash
python test_validation_agent.py
```

## Contributors
* Aerin Krebs 12/2025
* Carson Rodriguez 12/2025
* Sam Ballesteros 12/2025