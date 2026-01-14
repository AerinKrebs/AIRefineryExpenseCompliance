"""
Test Results Analyzer
Analyzes test results and generates insights for improving agents
CREATED BUT NOT USED YET
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

# Update paths for testing folder
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "test_results")


class TestResultsAnalyzer:
    """Analyzes test results to identify patterns and improvement opportunities"""
    
    def __init__(self, results_file: str):
        self.results_file = results_file
        self.data = None
        self.test_results = []
        self.summary = {}
    
    def load_results(self) -> bool:
        """Load test results from JSON file"""
        try:
            with open(self.results_file, 'r') as f:
                self.data = json.load(f)
                self.test_results = self.data.get('test_results', [])
                self.summary = self.data.get('summary', {})
            print(f"✓ Loaded results from: {self.results_file}")
            return True
        except Exception as e:
            print(f"✗ Error loading results: {e}")
            return False
    
    def analyze_failure_patterns(self) -> Dict:
        """Identify common patterns in failed tests"""
        
        failed_tests = [r for r in self.test_results if r['status'] in ['FAIL', 'PARTIAL']]
        
        patterns = {
            'by_category': defaultdict(list),
            'by_issue_type': defaultdict(list),
            'common_problems': defaultdict(int)
        }
        
        for result in failed_tests:
            category = result['test_case']['category']
            patterns['by_category'][category].append(result)
            
            if result.get('evaluation'):
                eval_data = result['evaluation']
                
                # Track key findings
                key_findings = eval_data.get('key_findings', {})
                for finding_type, finding_value in key_findings.items():
                    if finding_value in ['poor', 'failed']:
                        patterns['common_problems'][finding_type] += 1
                
                # Track specific issues
                for obs in eval_data.get('agent_observations', []):
                    # Extract issue type from observation
                    if 'missed' in obs.lower() or 'failed to' in obs.lower():
                        patterns['by_issue_type']['missed_detection'].append(result)
                    elif 'incorrect' in obs.lower() or 'wrong' in obs.lower():
                        patterns['by_issue_type']['incorrect_response'].append(result)
        
        return patterns
    
    def calculate_category_scores(self) -> Dict:
        """Calculate average scores by category"""
        
        category_scores = defaultdict(lambda: {'total': 0, 'count': 0, 'tests': []})
        
        for result in self.test_results:
            if result.get('score') is not None:
                category = result['test_case']['category']
                category_scores[category]['total'] += result['score']
                category_scores[category]['count'] += 1
                category_scores[category]['tests'].append({
                    'name': result['test_case']['edge_case'],
                    'score': result['score'],
                    'status': result['status']
                })
        
        # Calculate averages
        for category in category_scores:
            count = category_scores[category]['count']
            if count > 0:
                avg = category_scores[category]['total'] / count
                category_scores[category]['average'] = round(avg, 1)
        
        return dict(category_scores)
    
    def identify_improvement_areas(self) -> List[Dict]:
        """Identify specific areas for improvement"""
        
        improvements = []
        
        # Analyze failed tests for common themes
        failed_tests = [r for r in self.test_results if r['status'] in ['FAIL', 'PARTIAL']]
        
        for result in failed_tests:
            if result.get('evaluation'):
                suggestions = result['evaluation'].get('improvement_suggestions', [])
                for suggestion in suggestions:
                    improvements.append({
                        'test_case': result['test_case']['edge_case'],
                        'category': result['test_case']['category'],
                        'suggestion': suggestion,
                        'score': result.get('score', 0)
                    })
        
        return improvements
    
    def generate_insights_report(self, output_file: str = None):
        """Generate comprehensive insights report"""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(RESULTS_DIR, f"insights_report_{timestamp}.txt")
        
        patterns = self.analyze_failure_patterns()
        category_scores = self.calculate_category_scores()
        improvements = self.identify_improvement_areas()
        
        with open(output_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("TEST RESULTS ANALYSIS & INSIGHTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Overall Performance
            f.write("📊 OVERALL PERFORMANCE\n")
            f.write("-"*80 + "\n")
            total = self.summary.get('total_tests', 0)
            passed = self.summary.get('passed', 0)
            failed = self.summary.get('failed', 0)
            
            if total > 0:
                pass_rate = (passed / total) * 100
                f.write(f"Pass Rate: {pass_rate:.1f}% ({passed}/{total})\n")
                f.write(f"Failed: {failed} ({(failed/total)*100:.1f}%)\n")
            
            # Calculate average score
            scores = [r.get('score', 0) for r in self.test_results if r.get('score') is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                f.write(f"Average Score: {avg_score:.1f}/100\n")
            
            f.write("\n")
            
            # Category Performance
            f.write("📈 CATEGORY PERFORMANCE\n")
            f.write("-"*80 + "\n")
            
            # Sort categories by average score
            sorted_categories = sorted(
                category_scores.items(),
                key=lambda x: x[1].get('average', 0),
                reverse=True
            )
            
            for category, stats in sorted_categories:
                avg = stats.get('average', 0)
                count = stats.get('count', 0)
                
                # Determine rating
                if avg >= 90:
                    rating = "🟢 EXCELLENT"
                elif avg >= 75:
                    rating = "🟡 GOOD"
                elif avg >= 60:
                    rating = "🟠 NEEDS WORK"
                else:
                    rating = "🔴 CRITICAL"
                
                f.write(f"\n{category} - {rating}\n")
                f.write(f"  Average Score: {avg:.1f}/100 ({count} tests)\n")
                
                # Show individual test performance
                tests = stats.get('tests', [])
                failed_in_category = [t for t in tests if t['status'] in ['FAIL', 'PARTIAL']]
                if failed_in_category:
                    f.write(f"  Failed Tests:\n")
                    for test in failed_in_category:
                        f.write(f"    • {test['name']} (Score: {test['score']})\n")
            
            f.write("\n")
            
            # Common Problems
            f.write("🔍 COMMON PROBLEMS\n")
            f.write("-"*80 + "\n")
            
            common_probs = patterns['common_problems']
            if common_probs:
                sorted_problems = sorted(common_probs.items(), key=lambda x: x[1], reverse=True)
                for problem, count in sorted_problems:
                    f.write(f"  • {problem.replace('_', ' ').title()}: {count} occurrences\n")
            else:
                f.write("  No common problems identified\n")
            
            f.write("\n")
            
            # Failure Patterns by Category
            f.write("📊 FAILURE PATTERNS BY CATEGORY\n")
            f.write("-"*80 + "\n")
            
            for category, failed_tests in patterns['by_category'].items():
                if failed_tests:
                    f.write(f"\n{category} ({len(failed_tests)} failures):\n")
                    for result in failed_tests[:3]:  # Show top 3
                        f.write(f"  • {result['test_case']['edge_case']}\n")
                        if result.get('evaluation'):
                            reasoning = result['evaluation'].get('reasoning', '')
                            if reasoning:
                                f.write(f"    → {reasoning[:100]}...\n")
            
            f.write("\n")
            
            # Top Improvement Suggestions
            f.write("💡 TOP IMPROVEMENT RECOMMENDATIONS\n")
            f.write("-"*80 + "\n")
            
            # Group suggestions by similarity
            unique_suggestions = {}
            for imp in improvements:
                suggestion = imp['suggestion']
                # Group similar suggestions
                key = suggestion[:50]  # Use first 50 chars as key
                if key not in unique_suggestions:
                    unique_suggestions[key] = {
                        'text': suggestion,
                        'count': 0,
                        'categories': set(),
                        'avg_score': []
                    }
                unique_suggestions[key]['count'] += 1
                unique_suggestions[key]['categories'].add(imp['category'])
                unique_suggestions[key]['avg_score'].append(imp['score'])
            
            # Sort by frequency
            sorted_suggestions = sorted(
                unique_suggestions.values(),
                key=lambda x: x['count'],
                reverse=True
            )
            
            for i, sugg in enumerate(sorted_suggestions[:10], 1):
                avg_score = sum(sugg['avg_score']) / len(sugg['avg_score'])
                categories = ', '.join(sugg['categories'])
                f.write(f"\n{i}. {sugg['text']}\n")
                f.write(f"   Affects: {categories}\n")
                f.write(f"   Frequency: {sugg['count']} times | Avg Score: {avg_score:.1f}\n")
            
            f.write("\n")
            
            # Action Items
            f.write("✅ RECOMMENDED ACTIONS\n")
            f.write("-"*80 + "\n")
            
            # Generate action items based on analysis
            actions = []
            
            # Check for categories with low scores
            for category, stats in category_scores.items():
                avg = stats.get('average', 0)
                if avg < 70:
                    actions.append(f"PRIORITY: Improve {category} handling (current avg: {avg:.1f})")
            
            # Check for specific problem types
            if 'issue_detection' in common_probs and common_probs['issue_detection'] > 5:
                actions.append("CRITICAL: Enhance issue detection logic")
            
            if 'response_alignment' in common_probs and common_probs['response_alignment'] > 5:
                actions.append("CRITICAL: Align agent responses with expected behaviors")
            
            if 'data_quality' in common_probs and common_probs['data_quality'] > 5:
                actions.append("IMPORTANT: Improve data extraction quality")
            
            # Check pass rate
            if total > 0 and (passed / total) < 0.8:
                actions.append("CRITICAL: Overall pass rate below 80% - comprehensive review needed")
            
            if actions:
                for i, action in enumerate(actions, 1):
                    f.write(f"{i}. {action}\n")
            else:
                f.write("✓ Agent performance is good overall\n")
                f.write("• Continue monitoring edge cases\n")
                f.write("• Focus on maintaining quality\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"✓ Insights report saved to: {output_file}")
        return output_file
    
    def print_summary(self):
        """Print quick summary to console"""
        
        print("\n" + "="*80)
        print("QUICK ANALYSIS SUMMARY")
        print("="*80)
        
        total = self.summary.get('total_tests', 0)
        passed = self.summary.get('passed', 0)
        
        if total > 0:
            pass_rate = (passed / total) * 100
            print(f"\n📊 Pass Rate: {pass_rate:.1f}% ({passed}/{total})")
        
        # Category scores
        category_scores = self.calculate_category_scores()
        
        print("\n🏆 Best Performing Categories:")
        sorted_cats = sorted(
            category_scores.items(),
            key=lambda x: x[1].get('average', 0),
            reverse=True
        )
        
        for category, stats in sorted_cats[:3]:
            avg = stats.get('average', 0)
            print(f"  • {category}: {avg:.1f}/100")
        
        print("\n⚠️  Needs Improvement:")
        for category, stats in sorted_cats[-3:]:
            avg = stats.get('average', 0)
            if avg < 75:
                print(f"  • {category}: {avg:.1f}/100")
        
        print("\n" + "="*80 + "\n")


def main():
    """Main execution"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze test results')
    parser.add_argument('results_file', nargs='?', help='Path to test results JSON file')
    parser.add_argument('--latest', action='store_true', help='Analyze latest results file')
    
    args = parser.parse_args()
    
    # Find results file
    results_file = None
    
    if args.latest or not args.results_file:
        # Find most recent results file
        results_dir = Path(RESULTS_DIR)
        if results_dir.exists():
            json_files = list(results_dir.glob('test_results_*.json'))
            if json_files:
                results_file = str(max(json_files, key=os.path.getctime))
                print(f"Using latest results file: {results_file}")
    
    if not results_file and args.results_file:
        results_file = args.results_file
    
    if not results_file:
        print("❌ No results file found.")
        print("Run tests first: python test_agents.py")
        return
    
    # Analyze results
    analyzer = TestResultsAnalyzer(results_file)
    
    if not analyzer.load_results():
        return
    
    analyzer.print_summary()
    
    # Generate full report
    print("Generating detailed insights report...")
    report_file = analyzer.generate_insights_report()
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Full report: {report_file}")


if __name__ == "__main__":
    main()