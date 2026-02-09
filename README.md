# AIRefineryExpenseCompliance

An AI-powered expense compliance system that automates expense report validation, receipt processing, and policy compliance checking using AI Refinery agents.

## Features

- **AI-Powered Receipt Analysis**: Automatically extracts data from receipt images using OCR and AI
- **Expense Validation**: Validates expenses against company policies and spending limits
- **Compliance Checking**: Ensures all expenses meet regulatory and company requirements
- **Interactive Web Interface**: Streamlit-based UI for easy expense submission and policy queries
- **Comprehensive Testing Suite**: Automated testing framework for agent validation
- **Audit Logging**: Complete audit trail for compliance and debugging

## How to Run

### Prerequisites
- Python 3.8+
- API key for AI Refinery

### Setup

1. **Clone this repository**
   ```bash
   git clone https://github.com/AerinKrebs/AIRefineryExpenseCompliance.git
   cd AIRefineryExpenseCompliance
   ```

2. **Create environment file**
   Create a `.env` file in the root directory:
   ```plaintext
   API_KEY="your-api-key-here"
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run expense_compliance_app.py
   ```

The application will open in your browser at `http://localhost:8501`.

## Application Features

### Chat Assistant
- Ask questions about expense policies and compliance rules
- Get guidance on reimbursement procedures
- Query spending limits and approval workflows

### Expense Report Form
- Submit expense reports with receipt uploads
- Automatic validation and compliance checking
- Support for multiple expense categories and payment methods
- Real-time form validation

## Project Structure

```
AIRefineryExpenseCompliance/
├── agents.py                          # Core AI agent implementations
├── audit.py                           # Audit logging functionality
├── audit_log.json                     # Audit trail data
├── config.yaml                        # AI Refinery project configuration
├── create_air_project.py              # Script to create/update AI Refinery project
├── expense_compliance_app.py          # Main Streamlit web application
├── requirements.txt                   # Python dependencies
├── run_all_agents_test.py             # Comprehensive pipeline testing
├── Quick start testing.md             # Quick testing guide (placeholder)
├── agent_testing/                     # Agent testing suite
│   ├── test_agents.py                 # Main test runner
│   ├── quick_test.py                  # Interactive debugging tool
│   ├── analyze_results.py             # Results analysis and reporting
│   ├── quickstart.md                  # Testing quickstart guide
│   ├── edge_cases.json                # Test case definitions
│   ├── va_edge_cases.json             # Validation agent test cases
│   ├── audit_log.json                 # Test audit logs
│   └── test_results/                  # Generated test results
│       ├── va_test_results_*.json     # Validation agent results
│       ├── va_test_summary_*.txt      # Test summaries
├── test_results/                      # Pipeline test outputs
│   ├── pipeline_report_*.html         # HTML test reports
│   └── pipeline_results_*.json        # Pipeline test data
├── tests/                             # Unit tests and test data
│   ├── debug_validation.py            # Validation debugging utilities
│   ├── test_image_agent.py            # Image processing tests
│   ├── test_local_receipt.py          # Local receipt processing tests
│   ├── test_validation_agent.py       # Validation agent unit tests
│   ├── Expense_Reporting_Compliance_Policy.txt  # Policy document
│   └── validation_test_results.json   # Test results data
└── VAtesting/                         # Test images for validation
    ├── 1 Documentation.png
    ├── 2 Blurry.png
    ├── 3 Non English.png
    └── ... (50 test images total)
```

## Key Components

### Core Agents (`agents.py`)
- **Image Understanding Agent**: Extracts data from receipt images
- **Validation Agent**: Checks expenses against policies and limits
- **Data Analytics Agent**: Analyzes expense patterns and trends
- **Compliance Policy Agent**: Provides policy interpretations
- **Author Agent**: Generates compliance reports

### Configuration (`config.yaml`)
YAML configuration file defining agent behaviors, prompts, and AI Refinery settings.

### Testing Suite (`agent_testing/`)
Comprehensive testing framework for validating agent performance:

#### Quick Setup (30 seconds)
```bash
cd agent_testing
# Verify environment
cat ../.env | grep API_KEY
ls ../VAtesting/ | head -5
```

#### Running Tests
```bash
cd agent_testing

# Interactive menu (easiest)
./run_tests.sh

# Run all tests
python test_agents.py

# Run specific category
python test_agents.py --category "Documentation"

# Run single test
python test_agents.py --test-number 15

# Quick debugging
python quick_test.py 23
```

#### Analyzing Results
```bash
cd agent_testing

# Analyze latest results
python analyze_results.py --latest

# Analyze specific file
python analyze_results.py test_results/test_results_20260106_143022.json
```

### Output Files
Tests generate comprehensive reports in `agent_testing/test_results/`:
- `test_results_[timestamp].json` - Complete test data
- `test_summary_[timestamp].txt` - Human-readable summaries
- `insights_report_[timestamp].txt` - Performance analysis and recommendations

## Testing for Developers

### Agent Testing Suite
The `agent_testing/` directory contains a comprehensive testing framework:

1. **test_agents.py** - Main test runner for all agents
2. **quick_test.py** - Interactive debugging tool
3. **analyze_results.py** - Results analysis and reporting
4. **edge_cases.json** - Test case definitions
5. **va_edge_cases.json** - Validation agent specific tests

### Pipeline Testing
`run_all_agents_test.py` runs the complete agent pipeline on test images and generates HTML reports.

### Unit Tests
Individual unit tests in the `tests/` directory:
- `test_image_agent.py` - Image processing validation
- `test_validation_agent.py` - Policy compliance testing
- `test_local_receipt.py` - Local receipt processing

## API Integration

This project integrates with AI Refinery for AI agent orchestration. The system uses:
- Custom AI agents for specialized expense processing tasks
- Memory modules for context management
- Audit logging for compliance tracking
- Configurable agent behaviors via YAML

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite: `cd agent_testing && python test_agents.py`
5. Submit a pull request

## Troubleshooting

### Common Issues

**"No image file found"**
- Ensure test images are in the `VAtesting/` directory
- Verify filename format matches test expectations

**"Module not found" errors**
- Run commands from the correct directory
- Ensure all dependencies are installed

**API errors**
- Verify API_KEY in `.env` file
- Check API rate limits and quotas

**Import errors**
- Ensure you're in the project root or `agent_testing/` directory as appropriate
- Check that `agents.py` exists and is importable

## License

[Add license information here]

## Contributors
- Aerin Krebs (12/2025)
- Carson Rodriguez (12/2025)
- Sam Ballesteros (12/2025)

## Support

For questions or issues:
- Create an issue on GitHub
- Contact the development team