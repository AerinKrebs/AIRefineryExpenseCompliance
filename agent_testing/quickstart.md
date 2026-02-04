# Quick Start Guide - Agent Testing Suite

## 📁 Folder Structure

Your project should look like this:

```
YourProject/
├── agents.py                    ← Your agent code
├── audit.py
├── .env                         ← Contains API_KEY
├── VAtesting/                   ← Your test images
│   ├── 2 Blurry.png
│   ├── 5 Non English.png
│   ├── 10 Lodging Limit.png
│   └── ... (all 50 test images)
└── agent_testing/              ← Testing suite folder
    ├── test_agents.py          ← Main test runner
    ├── quick_test.py           ← Quick debugging tool
    ├── analyze_results.py      ← Results analyzer
    ├── run_tests.sh            ← Menu-driven runner
    ├── edge_cases.json         ← Test definitions
    ├── QUICKSTART.md           ← This file 
    └── test_results/           ← Auto-created output folder
        ├── test_results_*.json
        ├── test_summary_*.txt
        └── insights_report_*.txt
```

## 🚀 Quick Setup (30 seconds)

1. **Navigate to the testing folder:**
   ```bash
   cd agent_testing
   ```

2. **Verify your environment:**
   ```bash
   # Check .env file has API_KEY (in parent directory)
   cat ../.env | grep API_KEY
   
   # Check test images exist (in parent directory)
   ls ../VAtesting/ | head -5
   ```

3. **Ready to test!**

## 🎯 Three Ways to Run Tests

### Option 1: Interactive Menu (Easiest)
```bash
cd agent_testing
./run_tests.sh
```
Choose from menu options:
- Run all tests
- Test specific category
- Run single test
- Quick debugging

### Option 2: Command Line (Flexible)
```bash
cd agent_testing

# Run all tests
python test_agents.py

# Run specific category
python test_agents.py --category "Documentation"

# Run single test
python test_agents.py --test-number 15

# Run first 10 tests (quick check)
python test_agents.py --limit 10
```

### Option 3: Quick Debug (For Development)
```bash
cd agent_testing

# Interactive mode
python quick_test.py

# Direct test
python quick_test.py 23
```

## 📊 Analyzing Results

After running tests:

```bash
cd agent_testing

# Analyze latest results
python analyze_results.py --latest

# Analyze specific results file
python analyze_results.py test_results/test_results_20260106_143022.json
```

## 📁 Output Files

Tests create files in `agent_testing/test_results/`:

1. **`test_results_[timestamp].json`** - Complete data
   - Full agent responses
   - Evaluation details
   - All metadata

2. **`test_summary_[timestamp].txt`** - Human-readable
   - Pass/fail statistics
   - Category breakdown
   - Failed test details

Analysis creates:

3. **`insights_report_[timestamp].txt`** - Deep analysis
   - Performance patterns
   - Improvement recommendations
   - Action items

## 🔧 Common Commands

All commands run from the `agent_testing/` directory:

```bash
# Test Documentation category only
python test_agents.py --category "Documentation"

# Debug test #15 (Alcohol case)
python quick_test.py 15

# Run 5 tests to check setup
python test_agents.py --limit 5

# Analyze last test run
python analyze_results.py --latest
```

## ✅ Typical Workflow

1. **First time setup:**
   ```bash
   cd agent_testing
   python test_agents.py --limit 5  # Verify everything works
   ```

2. **Test specific functionality:**
   ```bash
   python test_agents.py --category "Documentation"
   ```

3. **Debug failures:**
   ```bash
   python quick_test.py 8  # Test that failed
   ```

4. **Full test run:**
   ```bash
   python test_agents.py  # All 50 tests
   ```

5. **Review results:**
   ```bash
   python analyze_results.py --latest
   cat test_results/insights_report_*.txt
   ```

## 🐛 Troubleshooting

**"No image file found"**
- Check image files are in `../VAtesting/` directory (parent folder)
- Verify filename format: `15 Alcohol.png`

**"Module not found" errors**
- Make sure you're in the `agent_testing/` directory
- Ensure `agents.py` exists in the parent directory
- Check that all imports are working

**API errors**
- Verify API_KEY in `../.env` (parent directory)
- Check API rate limits (script has 1s delay between tests)

**Import errors**
- Ensure you're running from the `agent_testing/` directory
- Check that agents.py is in the parent directory

## 💡 Pro Tips

- Always run commands from the `agent_testing/` directory
- Start with `--limit 5` to verify setup
- Use `quick_test.py` for debugging specific cases
- Review `insights_report_*.txt` for improvement guidance
- Run category tests when making targeted improvements
- Keep test results for tracking progress over time

## 📂 Directory Navigation

```bash
# From project root
cd agent_testing              # Go to testing folder
python test_agents.py         # Run tests

# From testing folder
cd ..                         # Go back to project root
cd agent_testing              # Return to testing folder
```

## 📞 Need Help?

Check the detailed documentation:
- `TEST_README.md` - Complete testing guide
- `test_agents.py` - Main test logic and examples
- `quick_test.py` - Debugging tool details

Happy testing! 🎉