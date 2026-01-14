"""
Unit Testing Script for Expense Compliance Agents
Tests image understanding and validation agents against edge cases
"""

import os
import sys
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the agents from parent directory
from agents import image_understanding_agent, validation_agent
from air import AsyncAIRefinery

# Load environment
load_dotenv()
API_KEY = str(os.getenv("API_KEY"))

# Configuration - updated paths
EDGE_CASES_FILE = os.path.join(os.path.dirname(__file__), "edge_cases.json")
TEST_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VAtesting")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "test_results")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


class AgentTester:
    """Orchestrates agent testing and evaluation"""
    
    def __init__(self):
        self.edge_cases = []
        self.test_results = []
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "categories": {}
        }
    
    def load_edge_cases(self, filepath: str) -> bool:
        """Load edge cases from JSON file"""
        try:
            with open(filepath, 'r') as f:
                self.edge_cases = json.load(f)
            print(f"✓ Loaded {len(self.edge_cases)} edge cases")
            return True
        except Exception as e:
            print(f"✗ Error loading edge cases: {e}")
            return False
    
    def find_test_image(self, image_number: int) -> Optional[str]:
        """Find the test image file for a given image number"""
        test_dir = Path(TEST_IMAGES_DIR)
        
        # Try different possible filename patterns
        patterns = [
            f"{image_number} *.png",
        ]
        
        for pattern in patterns:
            matches = list(test_dir.glob(pattern))
            if matches:
                return str(matches[0])
        
        return None
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image file to base64"""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error encoding image {image_path}: {e}")
            return ""
    
    async def run_agent_pipeline(self, edge_case: Dict, image_path: str) -> Dict:
        """Run both image understanding and validation agents"""
        
        # Encode image
        image_data = self.encode_image_to_base64(image_path)
        if not image_data:
            return {
                "success": False,
                "error": "Failed to encode image",
                "image_understanding_result": None,
                "validation_result": None
            }
        
        # Prepare environment variables
        env_vars = {
            "image_data": image_data,
            "image_type": "receipt",
            "user_id": "test_user"
        }
        
        try:
            # Step 1: Run image understanding agent
            print(f"  → Running Image Understanding Agent...")
            query = f"Extract expense data from this receipt. This is a test case for: {edge_case['edge_case']}"
            
            image_result = await image_understanding_agent(
                query=query,
                env_variable=env_vars,
                chat_history=None
            )
            
            image_result_dict = json.loads(image_result)
            
            # Step 2: Run validation agent if image understanding succeeded
            validation_result_dict = None
            if image_result_dict.get("success"):
                print(f"  → Running Validation Agent...")
                
                # Update env vars with extracted data
                env_vars["extracted_data"] = image_result_dict.get("extracted_data", {})
                
                validation_result = await validation_agent(
                    query=f"Validate this expense data. Context: {edge_case['edge_case']}",
                    env_variable=env_vars,
                    chat_history=None
                )
                
                validation_result_dict = json.loads(validation_result)
            
            return {
                "success": True,
                "image_understanding_result": image_result_dict,
                "validation_result": validation_result_dict
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "image_understanding_result": None,
                "validation_result": None
            }
    
    async def evaluate_agent_response(
        self,
        edge_case: Dict,
        agent_results: Dict
    ) -> Dict:
        """Use LLM to evaluate if agent response matches expected behavior"""
        
        evaluation_prompt = f"""
You are evaluating an AI agent's performance on an expense compliance test case.

**TEST CASE:**
- Category: {edge_case['category']}
- Edge Case: {edge_case['edge_case']}
- Description: {edge_case['description']}
- Expected Agent Behavior: {edge_case['expected_agent_behavior']}

**AGENT RESULTS:**
{json.dumps(agent_results, indent=2)}

**YOUR TASK:**
Evaluate whether the agent's response correctly handles this edge case according to the expected behavior.

**EVALUATION CRITERIA:**

1. **Did the agent detect the issue?**
   - Did it identify the problem described in the edge case?
   - Did it recognize the data quality or compliance concern?

2. **Did the agent respond appropriately?**
   - Does the response match the expected behavior (flag, block, request, reject, etc.)?
   - Are appropriate warnings or errors raised?
   - Is the severity level appropriate?

3. **Is the response actionable?**
   - Does it provide clear guidance on what's wrong?
   - Does it suggest corrective actions if applicable?

4. **Data handling:**
   - For image understanding: Was relevant data extracted despite issues?
   - For validation: Were appropriate corrections or flags made?

**SCORING:**
- **PASS**: Agent correctly identified the issue and responded per expected behavior
- **PARTIAL**: Agent identified issue but response was incomplete or not fully aligned
- **FAIL**: Agent missed the issue or responded incorrectly
- **ERROR**: Agent encountered technical errors preventing proper evaluation

Return a JSON object with this structure:
{{
  "test_result": "PASS" | "PARTIAL" | "FAIL" | "ERROR",
  "score": 0-100,
  "detected_issue": true/false,
  "appropriate_response": true/false,
  "reasoning": "Detailed explanation of evaluation",
  "agent_observations": [
    "What the agent correctly identified",
    "What the agent missed or got wrong"
  ],
  "improvement_suggestions": [
    "How the agent could improve"
  ],
  "key_findings": {{
    "issue_detection": "good/partial/poor/failed",
    "response_alignment": "good/partial/poor/failed",
    "data_quality": "good/partial/poor/failed"
  }}
}}

Return ONLY valid JSON, no markdown formatting.
"""
        
        try:
            client = AsyncAIRefinery(api_key=API_KEY)
            
            response = await client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert evaluator of AI agent performance. Be fair but thorough in your assessment."
                    },
                    {
                        "role": "user",
                        "content": evaluation_prompt
                    }
                ],
                temperature=0.2
            )
            
            eval_response = response.choices[0].message.content.strip()
            
            # Parse response
            import re
            clean_response = eval_response.strip()
            code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, clean_response)
            
            if match:
                clean_response = match.group(1).strip()
            
            clean_response = clean_response.strip('`').strip()
            evaluation = json.loads(clean_response)
            
            return evaluation
            
        except Exception as e:
            return {
                "test_result": "ERROR",
                "score": 0,
                "detected_issue": False,
                "appropriate_response": False,
                "reasoning": f"Evaluation error: {str(e)}",
                "agent_observations": [],
                "improvement_suggestions": [],
                "key_findings": {
                    "issue_detection": "failed",
                    "response_alignment": "failed",
                    "data_quality": "failed"
                }
            }
    
    async def run_test_case(self, edge_case: Dict) -> Dict:
        """Run a single test case"""
        
        image_number = edge_case.get('image_number')
        test_name = f"Test #{image_number}: {edge_case['edge_case']}"
        
        print(f"\n{'='*80}")
        print(f"Running {test_name}")
        print(f"Category: {edge_case['category']}")
        print(f"Expected: {edge_case['expected_agent_behavior']}")
        print(f"{'='*80}")
        
        # Find test image
        image_path = self.find_test_image(image_number)
        if not image_path:
            print(f"✗ Test image not found for #{image_number}")
            return {
                "test_case": edge_case,
                "status": "SKIPPED",
                "reason": "Image file not found",
                "image_path": None,
                "agent_results": None,
                "evaluation": None,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"✓ Found image: {image_path}")
        
        # Run agents
        print(f"Running agent pipeline...")
        agent_results = await self.run_agent_pipeline(edge_case, image_path)
        
        if not agent_results.get("success"):
            print(f"✗ Agent execution error: {agent_results.get('error', 'Unknown')}")
            return {
                "test_case": edge_case,
                "status": "ERROR",
                "reason": agent_results.get('error', 'Unknown error'),
                "image_path": image_path,
                "agent_results": agent_results,
                "evaluation": None,
                "timestamp": datetime.now().isoformat()
            }
        
        # Evaluate results
        print(f"Evaluating agent response...")
        evaluation = await self.evaluate_agent_response(edge_case, agent_results)
        
        result_status = evaluation.get("test_result", "ERROR")
        score = evaluation.get("score", 0)
        
        status_emoji = {
            "PASS": "✓",
            "PARTIAL": "◐",
            "FAIL": "✗",
            "ERROR": "⚠"
        }
        
        print(f"\n{status_emoji.get(result_status, '?')} Result: {result_status} (Score: {score}/100)")
        print(f"Reasoning: {evaluation.get('reasoning', 'N/A')}")
        
        return {
            "test_case": edge_case,
            "status": result_status,
            "score": score,
            "image_path": image_path,
            "agent_results": agent_results,
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_all_tests(self, limit: Optional[int] = None):
        """Run all test cases"""
        
        print("\n" + "="*80)
        print("EXPENSE COMPLIANCE AGENT - EDGE CASE TESTING")
        print("="*80)
        
        test_cases = self.edge_cases[:limit] if limit else self.edge_cases
        
        for i, edge_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}]")
            
            result = await self.run_test_case(edge_case)
            self.test_results.append(result)
            
            # Update summary
            category = edge_case['category']
            if category not in self.summary['categories']:
                self.summary['categories'][category] = {
                    "total": 0,
                    "passed": 0,
                    "partial": 0,
                    "failed": 0,
                    "errors": 0
                }
            
            self.summary['total_tests'] += 1
            self.summary['categories'][category]['total'] += 1
            
            status = result['status']
            if status == "PASS":
                self.summary['passed'] += 1
                self.summary['categories'][category]['passed'] += 1
            elif status == "PARTIAL":
                self.summary['categories'][category]['partial'] += 1
            elif status == "FAIL":
                self.summary['failed'] += 1
                self.summary['categories'][category]['failed'] += 1
            elif status in ["ERROR", "SKIPPED"]:
                self.summary['errors'] += 1
                self.summary['categories'][category]['errors'] += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
    
    def generate_report(self):
        """Generate comprehensive test report"""
        
        # Create results directory
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Save detailed results
        detailed_file = os.path.join(RESULTS_DIR, f"test_results_{TIMESTAMP}.json")
        with open(detailed_file, 'w') as f:
            json.dump({
                "summary": self.summary,
                "test_results": self.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n✓ Detailed results saved to: {detailed_file}")
        
        # Generate summary report
        summary_file = os.path.join(RESULTS_DIR, f"test_summary_{TIMESTAMP}.txt")
        with open(summary_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("EXPENSE COMPLIANCE AGENT - TEST SUMMARY\n")
            f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Overall summary
            f.write("OVERALL RESULTS:\n")
            f.write(f"  Total Tests: {self.summary['total_tests']}\n")
            f.write(f"  Passed: {self.summary['passed']} ({self.summary['passed']/max(self.summary['total_tests'],1)*100:.1f}%)\n")
            f.write(f"  Failed: {self.summary['failed']} ({self.summary['failed']/max(self.summary['total_tests'],1)*100:.1f}%)\n")
            f.write(f"  Errors/Skipped: {self.summary['errors']}\n\n")
            
            # Category breakdown
            f.write("RESULTS BY CATEGORY:\n")
            for category, stats in sorted(self.summary['categories'].items()):
                f.write(f"\n  {category}:\n")
                f.write(f"    Total: {stats['total']}\n")
                f.write(f"    Passed: {stats['passed']}\n")
                f.write(f"    Partial: {stats['partial']}\n")
                f.write(f"    Failed: {stats['failed']}\n")
                f.write(f"    Errors: {stats['errors']}\n")
            
            # Failed tests detail
            f.write("\n" + "="*80 + "\n")
            f.write("FAILED TESTS:\n")
            f.write("="*80 + "\n")
            
            for result in self.test_results:
                if result['status'] in ['FAIL', 'ERROR']:
                    f.write(f"\n✗ Test #{result['test_case']['image_number']}: {result['test_case']['edge_case']}\n")
                    f.write(f"  Category: {result['test_case']['category']}\n")
                    f.write(f"  Status: {result['status']}\n")
                    if result.get('evaluation'):
                        f.write(f"  Reasoning: {result['evaluation'].get('reasoning', 'N/A')}\n")
                    f.write(f"  Expected: {result['test_case']['expected_agent_behavior']}\n")
            
            # Top issues
            f.write("\n" + "="*80 + "\n")
            f.write("KEY FINDINGS:\n")
            f.write("="*80 + "\n")
            
            # Collect common issues
            issue_types = {}
            for result in self.test_results:
                if result.get('evaluation') and result['status'] != 'PASS':
                    key_findings = result['evaluation'].get('key_findings', {})
                    for finding_type, finding_value in key_findings.items():
                        if finding_value in ['poor', 'failed']:
                            issue_types[finding_type] = issue_types.get(finding_type, 0) + 1
            
            if issue_types:
                f.write("\nCommon Issues:\n")
                for issue, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"  - {issue}: {count} occurrences\n")
        
        print(f"✓ Summary report saved to: {summary_file}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.summary['total_tests']}")
        print(f"Passed: {self.summary['passed']} ({self.summary['passed']/max(self.summary['total_tests'],1)*100:.1f}%)")
        print(f"Failed: {self.summary['failed']} ({self.summary['failed']/max(self.summary['total_tests'],1)*100:.1f}%)")
        print(f"Errors/Skipped: {self.summary['errors']}")
        print("="*80)


async def main():
    """Main execution"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Test expense compliance agents')
    parser.add_argument('--limit', type=int, help='Limit number of tests to run')
    parser.add_argument('--category', type=str, help='Test only specific category')
    parser.add_argument('--test-number', type=int, help='Run specific test number')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = AgentTester()
    
    # Load edge cases
    if not tester.load_edge_cases(EDGE_CASES_FILE):
        print("Failed to load edge cases. Exiting.")
        return
    
    # Filter by category if specified
    if args.category:
        tester.edge_cases = [
            ec for ec in tester.edge_cases 
            if ec['category'].lower() == args.category.lower()
        ]
        print(f"Filtered to {len(tester.edge_cases)} tests in category: {args.category}")
    
    # Filter by test number if specified
    if args.test_number:
        tester.edge_cases = [
            ec for ec in tester.edge_cases 
            if ec['image_number'] == args.test_number
        ]
        print(f"Running single test: #{args.test_number}")
    
    if not tester.edge_cases:
        print("No test cases match the criteria. Exiting.")
        return
    
    # Run tests
    await tester.run_all_tests(limit=args.limit)
    
    # Generate report
    tester.generate_report()


if __name__ == "__main__":
    asyncio.run(main())