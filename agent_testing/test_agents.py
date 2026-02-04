"""
Unit Testing Script for Expense Compliance Agents
Tests all agents (Image Understanding, Validation, Data Analytics, Compliance Policy, Author) against edge cases
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

# Import all agents
try:
    from agents import image_understanding_agent, validation_agent
    from expense_agents import (
        data_analytics_agent,
        compliance_policy_agent,
        author_agent
    )
    print("✓ Successfully imported all agents (5 total)")
except ImportError as e:
    print(f"✗ Error importing agents: {e}")
    print("Note: Make sure both 'agents.py' and 'expense_agents.py' are available")
    sys.exit(1)

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
    """Orchestrates agent testing and evaluation for all 5 agents"""
    
    def __init__(self):
        self.edge_cases = []
        self.test_results = []
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "categories": {},
            "agent_performance": {
                "image_understanding": {"pass": 0, "fail": 0, "error": 0},
                "validation": {"pass": 0, "fail": 0, "error": 0},
                "data_analytics": {"pass": 0, "fail": 0, "error": 0},
                "compliance_policy": {"pass": 0, "fail": 0, "error": 0},
                "author": {"pass": 0, "fail": 0, "error": 0}
            }
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
            f"{image_number}.png",
            f"test_{image_number}.png",
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
    
    async def run_full_agent_pipeline(self, edge_case: Dict, image_path: str) -> Dict:
        """Run all 5 agents in sequence: Image Understanding → Validation → Analytics → Compliance → Author"""
        
        # Encode image
        image_data = self.encode_image_to_base64(image_path)
        if not image_data:
            return {
                "success": False,
                "error": "Failed to encode image",
                "results": {}
            }
        
        # Initialize results container
        pipeline_results = {
            "image_understanding": None,
            "validation": None,
            "data_analytics": None,
            "compliance_policy": None,
            "author": None
        }
        
        # Prepare environment variables
        env_vars = {
            "image_data": image_data,
            "image_type": "receipt",
            "user_id": "test_user_001",
            "user_name": "Test User",
            "user_role": "employee",
            "user_department": "engineering"
        }
        
        try:
            # ==================== STEP 1: Image Understanding Agent ====================
            print(f"  → [1/5] Running Image Understanding Agent...")
            query = f"Extract expense data from this receipt. Test case: {edge_case['edge_case']}"
            
            image_result = await image_understanding_agent(
                query=query,
                env_variable=env_vars,
                chat_history=None
            )
            
            image_result_dict = json.loads(image_result)
            pipeline_results["image_understanding"] = image_result_dict
            
            # Check if image understanding succeeded
            if not image_result_dict.get("success"):
                print(f"  ⚠ Image Understanding failed - stopping pipeline")
                return {
                    "success": False,
                    "error": "Image Understanding Agent failed",
                    "results": pipeline_results
                }
            
            extracted_data = image_result_dict.get("extracted_data", {})
            
            # ==================== STEP 2: Validation Agent ====================
            print(f"  → [2/5] Running Validation Agent...")
            
            env_vars["extracted_data"] = extracted_data
            
            validation_result = await validation_agent(
                query=f"Validate this expense data. Context: {edge_case['edge_case']}",
                env_variable=env_vars,
                chat_history=None
            )
            
            validation_result_dict = json.loads(validation_result)
            pipeline_results["validation"] = validation_result_dict
            
            validated_data = validation_result_dict.get("validated_data", extracted_data)
            
            # ==================== STEP 3: Data Analytics Agent ====================
            print(f"  → [3/5] Running Data Analytics Agent...")
            
            # Add mock expense history for context
            env_vars["validated_data"] = validated_data
            env_vars["expense_history"] = [
                {"date": "2026-01-28", "amount": 45.00, "category": "meals", "vendor": "Restaurant"},
                {"date": "2026-01-22", "amount": 32.50, "category": "meals", "vendor": "Cafe"},
                {"date": "2026-01-15", "amount": 67.00, "category": "meals", "vendor": "Bistro"}
            ]
            
            analytics_result = await data_analytics_agent(
                query=f"Analyze this expense for patterns and anomalies. Context: {edge_case['edge_case']}",
                env_variable=env_vars,
                chat_history=None
            )
            
            analytics_result_dict = json.loads(analytics_result)
            pipeline_results["data_analytics"] = analytics_result_dict
            
            # ==================== STEP 4: Compliance Policy Agent ====================
            print(f"  → [4/5] Running Compliance Policy Agent...")
            
            env_vars["analytics_results"] = analytics_result_dict.get("analytics_results", {})
            
            compliance_result = await compliance_policy_agent(
                query=f"Check compliance for this expense. Context: {edge_case['edge_case']}",
                env_variable=env_vars,
                chat_history=None
            )
            
            compliance_result_dict = json.loads(compliance_result)
            pipeline_results["compliance_policy"] = compliance_result_dict
            
            # ==================== STEP 5: Author Agent ====================
            print(f"  → [5/5] Running Author Agent...")
            
            env_vars["compliance_results"] = compliance_result_dict.get("compliance_results", {})
            
            author_result = await author_agent(
                query=f"Create notification for this expense submission. Context: {edge_case['edge_case']}",
                env_variable=env_vars,
                chat_history=None
            )
            
            author_result_dict = json.loads(author_result)
            pipeline_results["author"] = author_result_dict
            
            # ==================== Pipeline Complete ====================
            print(f"  ✓ All 5 agents completed successfully")
            
            return {
                "success": True,
                "results": pipeline_results
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "results": pipeline_results
            }
    
    async def evaluate_agent_response(
        self,
        edge_case: Dict,
        pipeline_results: Dict
    ) -> Dict:
        """Use LLM to evaluate if all agents responded appropriately to the edge case"""
        
        evaluation_prompt = f"""
You are evaluating a complete expense compliance pipeline consisting of 5 AI agents.

**TEST CASE:**
- Category: {edge_case['category']}
- Edge Case: {edge_case['edge_case']}
- Description: {edge_case['description']}
- Expected Agent Behavior: {edge_case['expected_agent_behavior']}

**PIPELINE RESULTS (All 5 Agents):**
{json.dumps(pipeline_results, indent=2)}

**YOUR TASK:**
Evaluate whether the complete agent pipeline correctly handles this edge case.

**EVALUATION CRITERIA FOR EACH AGENT:**

1. **Image Understanding Agent:**
   - Did it extract data despite the edge case issue?
   - Did it note the data quality problem?
   - Was extraction accuracy appropriate given the edge case?

2. **Validation Agent:**
   - Did it detect data quality issues?
   - Did it flag appropriate validation errors/warnings?
   - Were corrections made if possible?

3. **Data Analytics Agent (NEW):**
   - Did it identify anomalies or patterns related to the edge case?
   - Was the risk assessment appropriate?
   - Did it flag the expense for review if needed?

4. **Compliance Policy Agent (NEW):**
   - Did it check relevant policies for this edge case?
   - Was the approval routing appropriate?
   - Were policy violations correctly identified?

5. **Author Agent (NEW):**
   - Did it create appropriate notifications given the edge case?
   - Was the user guidance clear and helpful?
   - Did it communicate issues/actions needed effectively?

**PIPELINE INTEGRATION:**
- Did agents work together coherently?
- Was information properly passed between agents?
- Did later agents consider findings from earlier agents?

**OVERALL ASSESSMENT:**
- **PASS**: Pipeline correctly identified and handled the edge case across all agents
- **PARTIAL**: Most agents handled it well but some gaps or inconsistencies
- **FAIL**: Pipeline missed the issue or responded inappropriately
- **ERROR**: Technical errors prevented proper evaluation

Return a JSON object with this structure:
{{
  "overall_result": "PASS" | "PARTIAL" | "FAIL" | "ERROR",
  "overall_score": 0-100,
  
  "agent_evaluations": {{
    "image_understanding": {{
      "passed": true/false,
      "score": 0-100,
      "notes": "What this agent did well/poorly"
    }},
    "validation": {{
      "passed": true/false,
      "score": 0-100,
      "notes": "What this agent did well/poorly"
    }},
    "data_analytics": {{
      "passed": true/false,
      "score": 0-100,
      "notes": "What this agent did well/poorly"
    }},
    "compliance_policy": {{
      "passed": true/false,
      "score": 0-100,
      "notes": "What this agent did well/poorly"
    }},
    "author": {{
      "passed": true/false,
      "score": 0-100,
      "notes": "What this agent did well/poorly"
    }}
  }},
  
  "pipeline_integration": {{
    "coherence_score": 0-100,
    "information_flow": "excellent/good/poor/failed",
    "notes": "How well agents worked together"
  }},
  
  "detected_issue": true/false,
  "appropriate_response": true/false,
  
  "reasoning": "Detailed explanation of overall evaluation",
  
  "strengths": [
    "What the pipeline handled well"
  ],
  
  "weaknesses": [
    "What the pipeline missed or handled poorly"
  ],
  
  "improvement_suggestions": [
    "How the pipeline could improve"
  ],
  
  "key_findings": {{
    "issue_detection": "excellent/good/partial/poor/failed",
    "response_alignment": "excellent/good/partial/poor/failed",
    "data_quality": "excellent/good/partial/poor/failed",
    "policy_enforcement": "excellent/good/partial/poor/failed",
    "user_communication": "excellent/good/partial/poor/failed"
  }}
}}

Be thorough but fair. Consider that edge cases are challenging by nature.
Return ONLY valid JSON, no markdown formatting.
"""
        
        try:
            client = AsyncAIRefinery(api_key=API_KEY)
            
            response = await client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert evaluator of AI agent performance. Evaluate each agent individually and the pipeline as a whole."
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
            import traceback
            traceback.print_exc()
            return {
                "overall_result": "ERROR",
                "overall_score": 0,
                "agent_evaluations": {
                    agent: {"passed": False, "score": 0, "notes": f"Evaluation error: {str(e)}"}
                    for agent in ["image_understanding", "validation", "data_analytics", "compliance_policy", "author"]
                },
                "pipeline_integration": {
                    "coherence_score": 0,
                    "information_flow": "failed",
                    "notes": f"Evaluation error: {str(e)}"
                },
                "detected_issue": False,
                "appropriate_response": False,
                "reasoning": f"Evaluation error: {str(e)}",
                "strengths": [],
                "weaknesses": [],
                "improvement_suggestions": [],
                "key_findings": {
                    "issue_detection": "failed",
                    "response_alignment": "failed",
                    "data_quality": "failed",
                    "policy_enforcement": "failed",
                    "user_communication": "failed"
                }
            }
    
    async def run_test_case(self, edge_case: Dict) -> Dict:
        """Run a single test case through the complete pipeline"""
        
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
                "pipeline_results": None,
                "evaluation": None,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"✓ Found image: {image_path}")
        
        # Run full pipeline (all 5 agents)
        print(f"Running full agent pipeline (5 agents)...")
        pipeline_output = await self.run_full_agent_pipeline(edge_case, image_path)
        
        if not pipeline_output.get("success"):
            print(f"✗ Pipeline execution error: {pipeline_output.get('error', 'Unknown')}")
            return {
                "test_case": edge_case,
                "status": "ERROR",
                "reason": pipeline_output.get('error', 'Unknown error'),
                "image_path": image_path,
                "pipeline_results": pipeline_output.get('results'),
                "evaluation": None,
                "timestamp": datetime.now().isoformat()
            }
        
        # Evaluate results
        print(f"Evaluating complete pipeline response...")
        evaluation = await self.evaluate_agent_response(edge_case, pipeline_output.get('results', {}))
        
        result_status = evaluation.get("overall_result", "ERROR")
        score = evaluation.get("overall_score", 0)
        
        status_emoji = {
            "PASS": "✓",
            "PARTIAL": "◐",
            "FAIL": "✗",
            "ERROR": "⚠"
        }
        
        print(f"\n{status_emoji.get(result_status, '?')} Overall Result: {result_status} (Score: {score}/100)")
        print(f"Reasoning: {evaluation.get('reasoning', 'N/A')[:150]}...")
        
        # Print individual agent scores
        agent_evals = evaluation.get('agent_evaluations', {})
        print(f"\nAgent Scores:")
        for agent_name, agent_eval in agent_evals.items():
            agent_score = agent_eval.get('score', 0)
            agent_pass = "✓" if agent_eval.get('passed') else "✗"
            print(f"  {agent_pass} {agent_name.replace('_', ' ').title()}: {agent_score}/100")
        
        # Update agent performance stats
        for agent_name, agent_eval in agent_evals.items():
            if agent_name in self.summary['agent_performance']:
                if agent_eval.get('passed'):
                    self.summary['agent_performance'][agent_name]['pass'] += 1
                elif agent_eval.get('score', 0) > 0:
                    self.summary['agent_performance'][agent_name]['fail'] += 1
                else:
                    self.summary['agent_performance'][agent_name]['error'] += 1
        
        return {
            "test_case": edge_case,
            "status": result_status,
            "score": score,
            "image_path": image_path,
            "pipeline_results": pipeline_output.get('results'),
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_all_tests(self, limit: Optional[int] = None):
        """Run all test cases"""
        
        print("\n" + "="*80)
        print("EXPENSE COMPLIANCE PIPELINE - EDGE CASE TESTING")
        print("Testing 5 Agents: Image Understanding, Validation, Analytics, Compliance, Author")
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
            await asyncio.sleep(2)
        
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
            f.write("EXPENSE COMPLIANCE PIPELINE - TEST SUMMARY\n")
            f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Overall summary
            f.write("OVERALL RESULTS:\n")
            f.write(f"  Total Tests: {self.summary['total_tests']}\n")
            f.write(f"  Passed: {self.summary['passed']} ({self.summary['passed']/max(self.summary['total_tests'],1)*100:.1f}%)\n")
            f.write(f"  Failed: {self.summary['failed']} ({self.summary['failed']/max(self.summary['total_tests'],1)*100:.1f}%)\n")
            f.write(f"  Errors/Skipped: {self.summary['errors']}\n\n")
            
            # Agent performance summary
            f.write("INDIVIDUAL AGENT PERFORMANCE:\n")
            for agent_name, stats in sorted(self.summary['agent_performance'].items()):
                total_agent_tests = stats['pass'] + stats['fail'] + stats['error']
                if total_agent_tests > 0:
                    pass_rate = stats['pass'] / total_agent_tests * 100
                    f.write(f"\n  {agent_name.replace('_', ' ').title()}:\n")
                    f.write(f"    Pass: {stats['pass']} ({pass_rate:.1f}%)\n")
                    f.write(f"    Fail: {stats['fail']}\n")
                    f.write(f"    Error: {stats['error']}\n")
            
            # Category breakdown
            f.write("\n" + "="*80 + "\n")
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
            f.write("FAILED/PARTIAL TESTS:\n")
            f.write("="*80 + "\n")
            
            for result in self.test_results:
                if result['status'] in ['FAIL', 'PARTIAL', 'ERROR']:
                    f.write(f"\n{result['status']}: Test #{result['test_case']['image_number']}: {result['test_case']['edge_case']}\n")
                    f.write(f"  Category: {result['test_case']['category']}\n")
                    f.write(f"  Score: {result.get('score', 0)}/100\n")
                    if result.get('evaluation'):
                        f.write(f"  Reasoning: {result['evaluation'].get('reasoning', 'N/A')}\n")
                        
                        # Agent-specific issues
                        agent_evals = result['evaluation'].get('agent_evaluations', {})
                        failed_agents = [name for name, eval in agent_evals.items() if not eval.get('passed')]
                        if failed_agents:
                            f.write(f"  Failed Agents: {', '.join(failed_agents)}\n")
                    
                    f.write(f"  Expected: {result['test_case']['expected_agent_behavior']}\n")
            
            # Key findings
            f.write("\n" + "="*80 + "\n")
            f.write("KEY FINDINGS:\n")
            f.write("="*80 + "\n")
            
            # Collect common issues
            issue_types = {}
            agent_issues = {agent: 0 for agent in self.summary['agent_performance'].keys()}
            
            for result in self.test_results:
                if result.get('evaluation') and result['status'] != 'PASS':
                    # Track overall issues
                    key_findings = result['evaluation'].get('key_findings', {})
                    for finding_type, finding_value in key_findings.items():
                        if finding_value in ['poor', 'failed']:
                            issue_types[finding_type] = issue_types.get(finding_type, 0) + 1
                    
                    # Track agent-specific issues
                    agent_evals = result['evaluation'].get('agent_evaluations', {})
                    for agent_name, agent_eval in agent_evals.items():
                        if not agent_eval.get('passed') and agent_name in agent_issues:
                            agent_issues[agent_name] += 1
            
            if issue_types:
                f.write("\nCommon Issues Across Pipeline:\n")
                for issue, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"  - {issue}: {count} occurrences\n")
            
            if any(count > 0 for count in agent_issues.values()):
                f.write("\nAgent-Specific Issues:\n")
                for agent, count in sorted(agent_issues.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        f.write(f"  - {agent.replace('_', ' ').title()}: {count} failures\n")
        
        print(f"✓ Summary report saved to: {summary_file}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.summary['total_tests']}")
        print(f"Passed: {self.summary['passed']} ({self.summary['passed']/max(self.summary['total_tests'],1)*100:.1f}%)")
        print(f"Failed: {self.summary['failed']} ({self.summary['failed']/max(self.summary['total_tests'],1)*100:.1f}%)")
        print(f"Errors/Skipped: {self.summary['errors']}")
        
        print("\nAgent Performance:")
        for agent_name, stats in sorted(self.summary['agent_performance'].items()):
            total = stats['pass'] + stats['fail'] + stats['error']
            if total > 0:
                pass_rate = stats['pass'] / total * 100
                print(f"  {agent_name.replace('_', ' ').title()}: {stats['pass']}/{total} ({pass_rate:.1f}%)")
        
        print("="*80)


async def main():
    """Main execution"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Test expense compliance agents (all 5)')
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