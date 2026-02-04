"""
Comprehensive Agent Pipeline Test Runner
Processes all test images from VATesting folder and generates a detailed visual report
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

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all agents
try:
    from agents import (
        image_understanding_agent,
        validation_agent,
        data_analytics_agent,
        compliance_policy_agent,
        author_agent
    )
    print("✓ Successfully imported all 5 agents from agents.py")
except ImportError as e:
    print(f"✗ Error importing agents: {e}")
    sys.exit(1)

# Load environment
load_dotenv()
API_KEY = str(os.getenv("API_KEY"))

# Configuration
TEST_IMAGES_DIR = Path("VATesting")
RESULTS_DIR = Path("test_results")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


class PipelineTestRunner:
    """Runs all agents on test images and generates comprehensive reports"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None
    
    def find_all_test_images(self) -> List[Path]:
        """Find all PNG images in VATesting directory"""
        if not TEST_IMAGES_DIR.exists():
            print(f"✗ Directory not found: {TEST_IMAGES_DIR}")
            return []
        
        images = sorted(TEST_IMAGES_DIR.glob("*.png"))
        print(f"✓ Found {len(images)} test images in {TEST_IMAGES_DIR}")
        return images
    
    def encode_image(self, image_path: Path) -> str:
        """Encode image to base64"""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"✗ Error encoding {image_path.name}: {e}")
            return ""
    
    async def run_pipeline(self, image_path: Path) -> Dict:
        """Run all 5 agents on a single image"""
        
        print(f"\n{'='*80}")
        print(f"Testing: {image_path.name}")
        print(f"{'='*80}")
        
        # Encode image
        image_data = self.encode_image(image_path)
        if not image_data:
            return {
                "image_name": image_path.name,
                "success": False,
                "error": "Failed to encode image"
            }
        
        # Environment variables
        env_vars = {
            "image_data": image_data,
            "image_type": "receipt",
            "user_id": "test_user",
            "user_name": "Test User",
            "user_role": "employee",
            "user_department": "engineering",
            "expense_history": [
                {"date": "2026-01-28", "amount": 45.00, "category": "meals"},
                {"date": "2026-01-22", "amount": 32.50, "category": "meals"},
                {"date": "2026-01-15", "amount": 67.00, "category": "meals"}
            ]
        }
        
        results = {
            "image_name": image_path.name,
            "success": True,
            "agents": {}
        }
        
        try:
            # Agent 1: Image Understanding
            print("  [1/5] Image Understanding Agent...")
            img_result = await image_understanding_agent(
                query=f"Extract expense data from {image_path.name}",
                env_variable=env_vars,
                chat_history=None
            )
            img_data = json.loads(img_result)
            results["agents"]["image_understanding"] = self._extract_image_summary(img_data)
            
            if not img_data.get("success"):
                results["pipeline_stopped"] = "image_understanding"
                return results
            
            extracted_data = img_data.get("extracted_data", {})
            
            # Agent 2: Validation
            print("  [2/5] Validation Agent...")
            env_vars["extracted_data"] = extracted_data
            val_result = await validation_agent(
                query="Validate extracted data",
                env_variable=env_vars,
                chat_history=None
            )
            val_data = json.loads(val_result)
            results["agents"]["validation"] = self._extract_validation_summary(val_data)
            validated_data = val_data.get("validated_data", extracted_data)
            
            # Agent 3: Data Analytics
            print("  [3/5] Data Analytics Agent...")
            env_vars["validated_data"] = validated_data
            analytics_result = await data_analytics_agent(
                query="Analyze expense patterns and risk",
                env_variable=env_vars,
                chat_history=None
            )
            analytics_data = json.loads(analytics_result)
            results["agents"]["data_analytics"] = self._extract_analytics_summary(analytics_data)
            
            # Agent 4: Compliance Policy
            print("  [4/5] Compliance Policy Agent...")
            env_vars["analytics_results"] = analytics_data.get("analytics_results", {})
            compliance_result = await compliance_policy_agent(
                query="Check policy compliance",
                env_variable=env_vars,
                chat_history=None
            )
            compliance_data = json.loads(compliance_result)
            results["agents"]["compliance_policy"] = self._extract_compliance_summary(compliance_data)
            
            # Agent 5: Author
            print("  [5/5] Author Agent...")
            env_vars["compliance_results"] = compliance_data.get("compliance_results", {})
            author_result = await author_agent(
                query="Generate user notification",
                env_variable=env_vars,
                chat_history=None
            )
            author_data = json.loads(author_result)
            results["agents"]["author"] = self._extract_author_summary(author_data)
            
            print("  ✓ Pipeline completed successfully")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    def _extract_image_summary(self, data: Dict) -> Dict:
        """Extract key information from image understanding results"""
        extracted = data.get("extracted_data", {})
        return {
            "success": data.get("success", False),
            "vendor": extracted.get("vendor_name", "N/A"),
            "amount": extracted.get("total_amount", "N/A"),
            "date": extracted.get("date", "N/A"),
            "category": extracted.get("expense_category", "N/A"),
            "confidence": extracted.get("confidence_score", 0),
            "notes": extracted.get("notes", "")
        }
    
    def _extract_validation_summary(self, data: Dict) -> Dict:
        """Extract key information from validation results"""
        return {
            "is_valid": data.get("success", False),
            "status": data.get("status", "unknown"),
            "errors": len(data.get("validation_errors", [])),
            "warnings": len(data.get("validation_warnings", [])),
            "data_quality_score": data.get("data_quality", {}).get("score", 0)
        }
    
    def _extract_analytics_summary(self, data: Dict) -> Dict:
        """Extract key information from analytics results"""
        return {
            "risk_level": data.get("risk_level", "N/A"),
            "risk_score": data.get("risk_score", 0),
            "is_anomalous": data.get("is_anomalous", False),
            "insights_count": len(data.get("key_insights", [])),
            "top_insight": data.get("key_insights", ["N/A"])[0] if data.get("key_insights") else "N/A"
        }
    
    def _extract_compliance_summary(self, data: Dict) -> Dict:
        """Extract key information from compliance results"""
        return {
            "is_compliant": data.get("is_compliant", False),
            "status": data.get("status", "unknown"),
            "approval_level": data.get("approval_level", "N/A"),
            "violations": data.get("violations_count", 0),
            "recommendation": data.get("final_recommendation", "N/A")
        }
    
    def _extract_author_summary(self, data: Dict) -> Dict:
        """Extract key information from author results"""
        messages = data.get("messages", {})
        in_app = messages.get("in_app", {})
        return {
            "notification_type": data.get("notification_type", "N/A"),
            "title": in_app.get("title", "N/A"),
            "actions_required": len(data.get("user_actions", []))
        }
    
    async def run_all_tests(self, limit: Optional[int] = None):
        """Run pipeline on all test images"""
        
        self.start_time = datetime.now()
        
        print("\n" + "="*80)
        print("EXPENSE COMPLIANCE PIPELINE - COMPREHENSIVE TEST")
        print("="*80)
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Find images
        images = self.find_all_test_images()
        if not images:
            print("No test images found!")
            return
        
        if limit:
            images = images[:limit]
            print(f"Testing first {limit} images...")
        
        # Run tests
        for i, image_path in enumerate(images, 1):
            print(f"\n[{i}/{len(images)}]")
            result = await self.run_pipeline(image_path)
            self.test_results.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(1)
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print(f"ALL TESTS COMPLETED in {duration:.1f} seconds")
        print("="*80)
    
    def generate_html_report(self):
        """Generate a beautiful HTML report"""
        
        RESULTS_DIR.mkdir(exist_ok=True)
        
        html_file = RESULTS_DIR / f"pipeline_report_{TIMESTAMP}.html"
        
        # Calculate summary stats
        total_tests = len(self.test_results)
        successful = sum(1 for r in self.test_results if r.get("success"))
        
        # Count outcomes by agent
        agent_stats = {
            "image_understanding": {"success": 0, "fail": 0},
            "validation": {"valid": 0, "invalid": 0},
            "data_analytics": {"low": 0, "medium": 0, "high": 0},
            "compliance_policy": {"compliant": 0, "non_compliant": 0},
            "author": {"total": 0}
        }
        
        for result in self.test_results:
            if not result.get("success"):
                continue
            
            agents = result.get("agents", {})
            
            # Image Understanding
            if agents.get("image_understanding", {}).get("success"):
                agent_stats["image_understanding"]["success"] += 1
            else:
                agent_stats["image_understanding"]["fail"] += 1
            
            # Validation
            if agents.get("validation", {}).get("is_valid"):
                agent_stats["validation"]["valid"] += 1
            else:
                agent_stats["validation"]["invalid"] += 1
            
            # Analytics
            risk_level = agents.get("data_analytics", {}).get("risk_level", "MEDIUM")
            if risk_level == "LOW":
                agent_stats["data_analytics"]["low"] += 1
            elif risk_level == "HIGH":
                agent_stats["data_analytics"]["high"] += 1
            else:
                agent_stats["data_analytics"]["medium"] += 1
            
            # Compliance
            if agents.get("compliance_policy", {}).get("is_compliant"):
                agent_stats["compliance_policy"]["compliant"] += 1
            else:
                agent_stats["compliance_policy"]["non_compliant"] += 1
            
            # Author
            agent_stats["author"]["total"] += 1
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expense Compliance Pipeline Test Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}
        
        .summary-card .number {{
            font-size: 3em;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .summary-card .label {{
            font-size: 1.1em;
            color: #6c757d;
            font-weight: 500;
        }}
        
        .agent-section {{
            padding: 40px;
        }}
        
        .agent-section h2 {{
            font-size: 1.8em;
            margin-bottom: 25px;
            color: #2d3748;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .agent-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .agent-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .agent-card h3 {{
            font-size: 1.3em;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .agent-card .stat {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}
        
        .agent-card .stat:last-child {{
            border-bottom: none;
        }}
        
        .results-table {{
            padding: 40px;
            background: white;
        }}
        
        .results-table h2 {{
            font-size: 1.8em;
            margin-bottom: 25px;
            color: #2d3748;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }}
        
        thead {{
            background: #667eea;
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
        }}
        
        td {{
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        tr:hover {{
            background: #f7fafc;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: #48bb78;
            color: white;
        }}
        
        .badge-warning {{
            background: #ed8936;
            color: white;
        }}
        
        .badge-danger {{
            background: #f56565;
            color: white;
        }}
        
        .badge-info {{
            background: #4299e1;
            color: white;
        }}
        
        .badge-low {{
            background: #48bb78;
            color: white;
        }}
        
        .badge-medium {{
            background: #ed8936;
            color: white;
        }}
        
        .badge-high {{
            background: #f56565;
            color: white;
        }}
        
        .footer {{
            background: #2d3748;
            color: white;
            padding: 30px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Expense Compliance Pipeline Test Report</h1>
            <p class="subtitle">Comprehensive Analysis of All 5 Agents</p>
            <p class="subtitle">Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{total_tests}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="summary-card">
                <div class="number">{successful}</div>
                <div class="label">Successful</div>
            </div>
            <div class="summary-card">
                <div class="number">{total_tests - successful}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="number">{(successful/max(total_tests,1)*100):.1f}%</div>
                <div class="label">Success Rate</div>
            </div>
        </div>
        
        <div class="agent-section">
            <h2>📊 Agent Performance Overview</h2>
            <div class="agent-cards">
                <div class="agent-card">
                    <h3>1️⃣ Image Understanding</h3>
                    <div class="stat">
                        <span>Successful Extractions:</span>
                        <span><strong>{agent_stats['image_understanding']['success']}</strong></span>
                    </div>
                    <div class="stat">
                        <span>Failed Extractions:</span>
                        <span><strong>{agent_stats['image_understanding']['fail']}</strong></span>
                    </div>
                </div>
                
                <div class="agent-card">
                    <h3>2️⃣ Validation</h3>
                    <div class="stat">
                        <span>Valid Data:</span>
                        <span><strong>{agent_stats['validation']['valid']}</strong></span>
                    </div>
                    <div class="stat">
                        <span>Invalid/Flagged:</span>
                        <span><strong>{agent_stats['validation']['invalid']}</strong></span>
                    </div>
                </div>
                
                <div class="agent-card">
                    <h3>3️⃣ Data Analytics</h3>
                    <div class="stat">
                        <span>Low Risk:</span>
                        <span><strong>{agent_stats['data_analytics']['low']}</strong></span>
                    </div>
                    <div class="stat">
                        <span>Medium Risk:</span>
                        <span><strong>{agent_stats['data_analytics']['medium']}</strong></span>
                    </div>
                    <div class="stat">
                        <span>High Risk:</span>
                        <span><strong>{agent_stats['data_analytics']['high']}</strong></span>
                    </div>
                </div>
                
                <div class="agent-card">
                    <h3>4️⃣ Compliance Policy</h3>
                    <div class="stat">
                        <span>Compliant:</span>
                        <span><strong>{agent_stats['compliance_policy']['compliant']}</strong></span>
                    </div>
                    <div class="stat">
                        <span>Non-Compliant:</span>
                        <span><strong>{agent_stats['compliance_policy']['non_compliant']}</strong></span>
                    </div>
                </div>
                
                <div class="agent-card">
                    <h3>5️⃣ Author</h3>
                    <div class="stat">
                        <span>Notifications Created:</span>
                        <span><strong>{agent_stats['author']['total']}</strong></span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="results-table">
            <h2>📋 Detailed Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Image</th>
                        <th>Vendor</th>
                        <th>Amount</th>
                        <th>Validation</th>
                        <th>Risk Level</th>
                        <th>Compliance</th>
                        <th>Approval</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add rows for each test
        for result in self.test_results:
            if not result.get("success"):
                html_content += f"""
                    <tr>
                        <td><strong>{result['image_name']}</strong></td>
                        <td colspan="6"><span class="badge badge-danger">ERROR: {result.get('error', 'Unknown error')}</span></td>
                    </tr>
"""
                continue
            
            agents = result.get("agents", {})
            img = agents.get("image_understanding", {})
            val = agents.get("validation", {})
            analytics = agents.get("data_analytics", {})
            compliance = agents.get("compliance_policy", {})
            
            # Determine badges
            val_badge = "badge-success" if val.get("is_valid") else "badge-warning"
            val_text = "Valid" if val.get("is_valid") else f"Issues ({val.get('errors', 0)} errors)"
            
            risk_level = analytics.get("risk_level", "MEDIUM")
            risk_badge = f"badge-{risk_level.lower()}"
            
            comp_badge = "badge-success" if compliance.get("is_compliant") else "badge-warning"
            comp_text = "Compliant" if compliance.get("is_compliant") else "Needs Review"
            
            amount = img.get("amount")
            amount_str = f"${amount}" if isinstance(amount, (int, float)) else str(amount)
            
            html_content += f"""
                    <tr>
                        <td><strong>{result['image_name']}</strong></td>
                        <td>{img.get('vendor', 'N/A')}</td>
                        <td><strong>{amount_str}</strong></td>
                        <td><span class="badge {val_badge}">{val_text}</span></td>
                        <td><span class="badge {risk_badge}">{risk_level}</span></td>
                        <td><span class="badge {comp_badge}">{comp_text}</span></td>
                        <td>{compliance.get('approval_level', 'N/A')}</td>
                    </tr>
"""
        
        html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by Expense Compliance Pipeline Test Suite</p>
            <p>All 5 Agents: Image Understanding • Validation • Data Analytics • Compliance Policy • Author</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✓ HTML Report generated: {html_file}")
        return html_file
    
    def generate_json_report(self):
        """Generate detailed JSON report"""
        
        json_file = RESULTS_DIR / f"pipeline_results_{TIMESTAMP}.json"
        
        report_data = {
            "test_run": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
                "total_tests": len(self.test_results)
            },
            "results": self.test_results
        }
        
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"✓ JSON Report generated: {json_file}")
        return json_file


async def main():
    """Main execution"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Run all agents on VATesting images')
    parser.add_argument('--limit', type=int, help='Limit number of images to test')
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = PipelineTestRunner()
    
    # Run all tests
    await runner.run_all_tests(limit=args.limit)
    
    # Generate reports
    print("\nGenerating reports...")
    html_file = runner.generate_html_report()
    json_file = runner.generate_json_report()
    
    print("\n" + "="*80)
    print("REPORTS GENERATED")
    print("="*80)
    print(f"📊 HTML Report: {html_file}")
    print(f"📄 JSON Report: {json_file}")
    print("="*80)
    print("\nOpen the HTML file in your browser to view the full report!")


if __name__ == "__main__":
    asyncio.run(main())