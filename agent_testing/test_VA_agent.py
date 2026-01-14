"""
Image Understanding Agent (VA) Testing Script
Tests ONLY the image understanding/extraction capabilities
Does NOT test validation logic
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

# Import only the image understanding agent
from agents import image_understanding_agent
from air import AsyncAIRefinery

# Load environment
load_dotenv()
API_KEY = str(os.getenv("API_KEY"))

# Configuration - updated paths
EDGE_CASES_FILE = os.path.join(os.path.dirname(__file__), "va_edge_cases.json")
TEST_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VAtesting")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "test_results")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


class VAAgentTester:
    """Tests Image Understanding Agent (VA) for extraction capabilities"""
    
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
            print(f"✓ Loaded {len(self.edge_cases)} VA test cases")
            return True
        except Exception as e:
            print(f"✗ Error loading edge cases: {e}")
            return False
    
    def find_test_image(self, image_number: int) -> Optional[str]:
        """Find the test image file for a given image number"""
        test_dir = Path(TEST_IMAGES_DIR)
        
        # Try different possible filename patterns but fixed for being "greedy"
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
    
    async def run_va_agent(self, edge_case: Dict, image_path: str) -> Dict:
        """Run ONLY the image understanding agent"""
        
        # Encode image
        image_data = self.encode_image_to_base64(image_path)
        if not image_data:
            return {
                "success": False,
                "error": "Failed to encode image",
                "extracted_data": None
            }
        
        # Prepare environment variables
        env_vars = {
            "image_data": image_data,
            "image_type": "receipt",
            "user_id": "va_test_user"
        }
        
        try:
            # Run image understanding agent
            print(f"  → Running Image Understanding Agent...")
            query = f"Extract all expense data from this receipt. Test case: {edge_case['test_case']}"
            
            result = await image_understanding_agent(
                query=query,
                env_variable=env_vars,
                chat_history=None
            )
            
            result_dict = json.loads(result)
            
            return {
                "success": result_dict.get("success", False),
                "extracted_data": result_dict.get("extracted_data", {}),
                "processing_notes": result_dict.get("processing_notes", []),
                "image_type": result_dict.get("image_type", "unknown"),
                "error": result_dict.get("error")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_data": None
            }
    
    async def evaluate_extraction_quality(
        self,
        edge_case: Dict,
        extraction_result: Dict
    ) -> Dict:
        """Use LLM to evaluate if data extraction was successful"""
        
        evaluation_prompt = f"""
You are evaluating an Image Understanding Agent's ability to extract data from receipts and invoices.

**TEST CASE:**
- Category: {edge_case['category']}
- Test: {edge_case['test_case']}
- Description: {edge_case['description']}
- Expected Behavior: {edge_case['expected_behavior']}

**EVALUATION CRITERIA:**
{json.dumps(edge_case.get('evaluation_criteria', {}), indent=2)}

**AGENT EXTRACTION RESULT:**
{json.dumps(extraction_result, indent=2)}

**YOUR TASK:**
Evaluate the agent's data extraction performance. Focus ONLY on extraction quality, NOT on validation or policy compliance.

**EVALUATION AREAS:**

1. **Data Extraction Completeness:**
   - Did it extract the key fields (vendor, date, amount, items)?
   - Are the extracted values present and reasonable?
   - What critical data is missing?

2. **OCR/Text Recognition Quality:**
   - How accurate is the text extraction?
   - Did it handle image quality issues appropriately?
   - Is the raw_text_extracted comprehensive?

3. **Field Identification:**
   - Did it correctly identify field types (amounts, dates, vendor)?
   - Are amounts properly parsed as numbers?
   - Are dates in correct format?

4. **Categorization:**
   - Is the expense category appropriate for the receipt type?
   - Does the categorization make sense?

5. **Confidence and Notes:**
   - Is the confidence score reasonable for the image quality?
   - Are appropriate issues flagged in notes?
   - Did it identify quality problems?

6. **Criteria Match:**
   - Check each criterion in evaluation_criteria
   - Score how well the agent met each specific criterion

**SCORING:**
- **EXCELLENT (90-100)**: Extracted all key data accurately, handled edge cases well
- **GOOD (75-89)**: Extracted most data, minor issues or missing optional fields
- **FAIR (60-74)**: Extracted core data but missed important details or made errors
- **POOR (40-59)**: Significant extraction failures, missing critical data
- **FAILED (0-39)**: Unable to extract meaningful data or major errors

Return a JSON object with this structure:
{{
  "test_result": "PASS" | "PARTIAL" | "FAIL",
  "score": 0-100,
  "extraction_quality": {{
    "completeness": "excellent/good/fair/poor",
    "accuracy": "excellent/good/fair/poor",
    "field_identification": "excellent/good/fair/poor",
    "ocr_quality": "excellent/good/fair/poor"
  }},
  "criteria_evaluation": {{
    "criterion_name": "met/partially_met/not_met"
  }},
  "extracted_successfully": [
    "List of fields extracted correctly"
  ],
  "extraction_failures": [
    "List of fields that failed or are wrong"
  ],
  "notes_quality": {{
    "flagged_issues": true/false,
    "appropriate_warnings": true/false,
    "confidence_score_reasonable": true/false
  }},
  "reasoning": "Detailed explanation of the evaluation",
  "strengths": [
    "What the agent did well"
  ],
  "weaknesses": [
    "What the agent missed or got wrong"
  ],
  "improvement_suggestions": [
    "How extraction could be improved"
  ]
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
                        "content": "You are an expert evaluator of OCR and data extraction systems. Evaluate extraction quality, not validation or compliance."
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
                "extraction_quality": {
                    "completeness": "failed",
                    "accuracy": "failed",
                    "field_identification": "failed",
                    "ocr_quality": "failed"
                },
                "reasoning": f"Evaluation error: {str(e)}",
                "extracted_successfully": [],
                "extraction_failures": ["Evaluation failed"],
                "strengths": [],
                "weaknesses": [],
                "improvement_suggestions": []
            }
    
    async def run_test_case(self, edge_case: Dict) -> Dict:
        """Run a single test case"""
        
        image_number = edge_case.get('image_number')
        test_name = f"VA Test #{image_number}: {edge_case['test_case']}"
        
        print(f"\n{'='*80}")
        print(f"Running {test_name}")
        print(f"Category: {edge_case['category']}")
        print(f"Expected: {edge_case['expected_behavior']}")
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
                "extraction_result": None,
                "evaluation": None,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"✓ Found image: {image_path}")
        
        # Run VA agent
        print(f"Running extraction...")
        extraction_result = await self.run_va_agent(edge_case, image_path)
        
        if not extraction_result.get("success"):
            print(f"✗ Extraction error: {extraction_result.get('error', 'Unknown')}")
            return {
                "test_case": edge_case,
                "status": "ERROR",
                "reason": extraction_result.get('error', 'Unknown error'),
                "image_path": image_path,
                "extraction_result": extraction_result,
                "evaluation": None,
                "timestamp": datetime.now().isoformat()
            }
        
        # Evaluate extraction quality
        print(f"Evaluating extraction quality...")
        evaluation = await self.evaluate_extraction_quality(edge_case, extraction_result)
        
        result_status = evaluation.get("test_result", "ERROR")
        score = evaluation.get("score", 0)
        
        status_emoji = {
            "PASS": "✓",
            "PARTIAL": "◐",
            "FAIL": "✗",
            "ERROR": "⚠"
        }
        
        print(f"\n{status_emoji.get(result_status, '?')} Result: {result_status} (Score: {score}/100)")
        print(f"Reasoning: {evaluation.get('reasoning', 'N/A')[:150]}...")
        
        return {
            "test_case": edge_case,
            "status": result_status,
            "score": score,
            "image_path": image_path,
            "extraction_result": extraction_result,
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_all_tests(self, limit: Optional[int] = None):
        """Run all test cases"""
        
        print("\n" + "="*80)
        print("IMAGE UNDERSTANDING AGENT (VA) - EXTRACTION TESTING")
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
        print("ALL VA TESTS COMPLETED")
        print("="*80)
    
    def generate_report(self):
        """Generate comprehensive test report"""
        
        # Create results directory
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Save detailed results
        detailed_file = os.path.join(RESULTS_DIR, f"va_test_results_{TIMESTAMP}.json")
        with open(detailed_file, 'w') as f:
            json.dump({
                "summary": self.summary,
                "test_results": self.test_results,
                "timestamp": datetime.now().isoformat(),
                "test_type": "Image Understanding Agent (VA) Only"
            }, f, indent=2)
        
        print(f"\n✓ Detailed results saved to: {detailed_file}")
        
        # Generate summary report
        summary_file = os.path.join(RESULTS_DIR, f"va_test_summary_{TIMESTAMP}.txt")
        with open(summary_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("IMAGE UNDERSTANDING AGENT (VA) - TEST SUMMARY\n")
            f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            f.write("TEST SCOPE:\n")
            f.write("  - Image Understanding Agent (VA) ONLY\n")
            f.write("  - Tests extraction and OCR capabilities\n")
            f.write("  - Does NOT test validation logic\n\n")
            
            # Overall summary
            f.write("OVERALL RESULTS:\n")
            f.write(f"  Total Tests: {self.summary['total_tests']}\n")
            f.write(f"  Passed: {self.summary['passed']} ({self.summary['passed']/max(self.summary['total_tests'],1)*100:.1f}%)\n")
            f.write(f"  Failed: {self.summary['failed']} ({self.summary['failed']/max(self.summary['total_tests'],1)*100:.1f}%)\n")
            f.write(f"  Errors/Skipped: {self.summary['errors']}\n\n")
            
            # Calculate average score
            scores = [r.get('score', 0) for r in self.test_results if r.get('score') is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                f.write(f"  Average Extraction Score: {avg_score:.1f}/100\n\n")
            
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
            f.write("EXTRACTION FAILURES:\n")
            f.write("="*80 + "\n")
            
            for result in self.test_results:
                if result['status'] in ['FAIL', 'PARTIAL']:
                    f.write(f"\n• Test #{result['test_case']['image_number']}: {result['test_case']['test_case']}\n")
                    f.write(f"  Category: {result['test_case']['category']}\n")
                    f.write(f"  Status: {result['status']} (Score: {result.get('score', 0)})\n")
                    
                    if result.get('evaluation'):
                        eval_data = result['evaluation']
                        
                        # Show what failed
                        failures = eval_data.get('extraction_failures', [])
                        if failures:
                            f.write(f"  Failed to extract:\n")
                            for failure in failures[:3]:
                                f.write(f"    - {failure}\n")
                        
                        # Show extraction quality
                        quality = eval_data.get('extraction_quality', {})
                        f.write(f"  Quality: Completeness={quality.get('completeness', 'N/A')}, ")
                        f.write(f"Accuracy={quality.get('accuracy', 'N/A')}\n")
            
            # Top issues
            f.write("\n" + "="*80 + "\n")
            f.write("COMMON EXTRACTION ISSUES:\n")
            f.write("="*80 + "\n")
            
            # Collect common weaknesses
            all_weaknesses = []
            for result in self.test_results:
                if result.get('evaluation'):
                    weaknesses = result['evaluation'].get('weaknesses', [])
                    all_weaknesses.extend(weaknesses)
            
            # Count occurrences
            weakness_counts = {}
            for weakness in all_weaknesses:
                key = weakness[:50]  # First 50 chars as key
                weakness_counts[key] = weakness_counts.get(key, 0) + 1
            
            if weakness_counts:
                sorted_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)
                for weakness, count in sorted_weaknesses[:10]:
                    f.write(f"  - {weakness}... ({count} occurrences)\n")
        
        print(f"✓ Summary report saved to: {summary_file}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("VA TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.summary['total_tests']}")
        print(f"Passed: {self.summary['passed']} ({self.summary['passed']/max(self.summary['total_tests'],1)*100:.1f}%)")
        print(f"Failed: {self.summary['failed']} ({self.summary['failed']/max(self.summary['total_tests'],1)*100:.1f}%)")
        print(f"Errors/Skipped: {self.summary['errors']}")
        
        if scores:
            print(f"Average Score: {sum(scores)/len(scores):.1f}/100")
        
        print("="*80)


async def main():
    """Main execution"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Image Understanding Agent (VA) extraction capabilities')
    parser.add_argument('--limit', type=int, help='Limit number of tests to run')
    parser.add_argument('--category', type=str, help='Test only specific category')
    parser.add_argument('--test-number', type=int, help='Run specific test number')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = VAAgentTester()
    
    # Load edge cases
    if not tester.load_edge_cases(EDGE_CASES_FILE):
        print("Failed to load VA edge cases. Exiting.")
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