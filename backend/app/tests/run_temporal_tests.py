"""
Comprehensive Test Runner for Temporal Universe System
Sprint 2.5 Part D - Complete Test Suite Execution

Runs all temporal universe tests with comprehensive reporting,
performance analysis, and quality gate validation.
"""
import os
import sys
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List, Any
import argparse


class TemporalTestRunner:
    """Comprehensive test runner for temporal universe system"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
        # Test categories and their files
        self.test_categories = {
            "API Endpoints": {
                "file": "test_universe_api_temporal.py",
                "markers": ["api_endpoints", "temporal"],
                "description": "API endpoint functionality, authentication, input validation",
                "sla_target": "95% pass rate, <200ms response time"
            },
            "Integration Workflows": {
                "file": "test_temporal_universe_integration.py", 
                "markers": ["integration", "temporal"],
                "description": "End-to-end temporal workflows and data consistency",
                "sla_target": "100% pass rate, cross-user isolation verified"
            },
            "Business Logic": {
                "file": "test_temporal_universe_business_logic.py",
                "markers": ["business_logic", "temporal"], 
                "description": "Mathematical accuracy, financial constraints, calculation logic",
                "sla_target": "100% accuracy, all financial formulas validated"
            },
            "Security": {
                "file": "test_temporal_universe_security.py",
                "markers": ["security", "temporal"],
                "description": "Authentication, authorization, input sanitization, SQL injection prevention",
                "sla_target": "100% pass rate, zero security vulnerabilities"
            },
            "Performance": {
                "file": "test_temporal_universe_performance.py", 
                "markers": ["performance", "temporal"],
                "description": "Response times, scalability, memory usage, concurrent load",
                "sla_target": "<200ms API response (95th), <5s backfill operations"
            }
        }
    
    def print_banner(self):
        """Print test execution banner"""
        print("=" * 80)
        print("🚀 TEMPORAL UNIVERSE COMPREHENSIVE TEST SUITE")
        print("   Sprint 2.5 Part D - API Layer Implementation Testing")
        print("=" * 80)
        print(f"Execution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Print test categories
        print("📋 TEST CATEGORIES:")
        for category, info in self.test_categories.items():
            print(f"   • {category}: {info['description']}")
            print(f"     Target: {info['sla_target']}")
        print()
    
    def run_category_tests(self, category: str, info: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
        """Run tests for a specific category"""
        print(f"🔍 Running {category} Tests...")
        print(f"   File: {info['file']}")
        print(f"   Markers: {', '.join(info['markers'])}")
        
        # Build pytest command
        cmd = [
            "python", "-m", "pytest",
            f"app/tests/{info['file']}",
            "-v", "--tb=short",
            "--durations=10"
        ]
        
        # Add marker filters
        if info['markers']:
            marker_filter = " and ".join(info['markers'])
            cmd.extend(["-m", marker_filter])
        
        # Add coverage if requested
        if args.coverage:
            cmd.extend([
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov"
            ])
        
        # Add performance flags for performance tests
        if "performance" in info['markers']:
            cmd.extend(["--benchmark-only", "--benchmark-sort=mean"])
        
        # Execute tests
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')
            
            # Extract test counts from pytest output
            test_summary = self.parse_pytest_output(output_lines)
            
            category_result = {
                "status": "PASSED" if result.returncode == 0 else "FAILED",
                "execution_time": execution_time,
                "return_code": result.returncode,
                "tests_run": test_summary.get("tests_run", 0),
                "passed": test_summary.get("passed", 0),
                "failed": test_summary.get("failed", 0),
                "skipped": test_summary.get("skipped", 0),
                "errors": test_summary.get("errors", []),
                "warnings": test_summary.get("warnings", []),
                "output": result.stdout,
                "stderr": result.stderr
            }
            
            # Update totals
            self.total_tests += category_result["tests_run"]
            self.passed_tests += category_result["passed"]
            self.failed_tests += category_result["failed"]
            self.skipped_tests += category_result["skipped"]
            
            # Print summary
            status_icon = "✅" if category_result["status"] == "PASSED" else "❌"
            print(f"   {status_icon} {category} - {category_result['status']}")
            print(f"      Tests: {category_result['tests_run']} total, {category_result['passed']} passed, {category_result['failed']} failed")
            print(f"      Time: {execution_time:.1f}s")
            
            if category_result["failed"] > 0:
                print(f"      ⚠️ {category_result['failed']} test(s) failed - check details below")
            
            print()
            
        except subprocess.TimeoutExpired:
            category_result = {
                "status": "TIMEOUT",
                "execution_time": 600,
                "return_code": -1,
                "tests_run": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": ["Test execution timeout after 10 minutes"],
                "warnings": [],
                "output": "",
                "stderr": "Process timed out"
            }
            
            print(f"   ⏰ {category} - TIMEOUT (>10 minutes)")
            print()
        
        except Exception as e:
            category_result = {
                "status": "ERROR",
                "execution_time": 0,
                "return_code": -2,
                "tests_run": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": [str(e)],
                "warnings": [],
                "output": "",
                "stderr": str(e)
            }
            
            print(f"   💥 {category} - ERROR: {e}")
            print()
        
        return category_result
    
    def parse_pytest_output(self, output_lines: List[str]) -> Dict[str, Any]:
        """Parse pytest output to extract test counts and information"""
        summary = {
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "warnings": []
        }
        
        # Look for test result summary line
        for line in output_lines:
            # Parse pytest summary line (e.g., "10 passed, 2 failed, 1 skipped")
            if "passed" in line or "failed" in line or "error" in line:
                if "failed" in line and "passed" in line:
                    # Extract numbers
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            count = int(part)
                            if i + 1 < len(parts):
                                result_type = parts[i + 1].rstrip(',')
                                if result_type == "passed":
                                    summary["passed"] = count
                                elif result_type == "failed":
                                    summary["failed"] = count
                                elif result_type == "skipped":
                                    summary["skipped"] = count
            
            # Collect warnings and errors
            if "WARNING" in line:
                summary["warnings"].append(line.strip())
            elif "ERROR" in line or "FAILED" in line:
                summary["errors"].append(line.strip())
        
        # Calculate total tests
        summary["tests_run"] = summary["passed"] + summary["failed"] + summary["skipped"]
        
        return summary
    
    def run_docker_tests(self, args: argparse.Namespace) -> bool:
        """Run tests in Docker environment"""
        print("🐳 Running tests in Docker environment...")
        print("   This ensures database isolation and production-like conditions")
        print()
        
        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker not available. Please install Docker to run tests.")
            return False
        
        # Build test command
        docker_cmd = [
            "docker-compose", "--profile", "test", "run", "test",
            "-k", "temporal",  # Run all temporal tests
            "--tb=short", "-v"
        ]
        
        if args.coverage:
            docker_cmd.extend(["--cov=app", "--cov-report=html"])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                docker_cmd,
                timeout=900,  # 15 minute timeout for Docker tests
                text=True
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ Docker tests completed successfully in {execution_time:.1f}s")
                return True
            else:
                print(f"❌ Docker tests failed (exit code {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Docker tests timed out after 15 minutes")
            return False
        except Exception as e:
            print(f"💥 Docker test execution error: {e}")
            return False
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        total_time = time.time() - self.start_time
        
        print("=" * 80)
        print("📊 TEMPORAL UNIVERSE TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        # Overall statistics
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"🕐 Total Execution Time: {total_time:.1f} seconds")
        print(f"📈 Overall Statistics:")
        print(f"   • Total Tests: {self.total_tests}")
        print(f"   • Passed: {self.passed_tests} ({success_rate:.1f}%)")
        print(f"   • Failed: {self.failed_tests}")
        print(f"   • Skipped: {self.skipped_tests}")
        print()
        
        # Category breakdown
        print("📋 Category Results:")
        for category, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "⏰"
            print(f"   {status_icon} {category}:")
            print(f"      Status: {result['status']}")
            print(f"      Tests: {result['passed']}/{result['tests_run']} passed")
            print(f"      Time: {result['execution_time']:.1f}s")
            if result["failed"] > 0:
                print(f"      Failed: {result['failed']} test(s)")
        
        print()
        
        # Quality gates validation
        print("🎯 QUALITY GATES VALIDATION:")
        
        gates = [
            ("Overall Success Rate", success_rate >= 95, f"{success_rate:.1f}% >= 95%"),
            ("API Performance", self.validate_api_performance(), "All endpoints <200ms"),
            ("Security Tests", self.validate_security_tests(), "No vulnerabilities detected"),
            ("Business Logic", self.validate_business_logic(), "All calculations accurate"),
            ("Integration Tests", self.validate_integration_tests(), "End-to-end workflows verified")
        ]
        
        all_gates_passed = True
        
        for gate_name, passed, description in gates:
            icon = "✅" if passed else "❌"
            print(f"   {icon} {gate_name}: {description}")
            if not passed:
                all_gates_passed = False
        
        print()
        
        # Final verdict
        if all_gates_passed and self.failed_tests == 0:
            print("🎉 ALL QUALITY GATES PASSED - TEMPORAL UNIVERSE SYSTEM READY FOR DEPLOYMENT!")
            verdict = "PASSED"
        else:
            print("⚠️ QUALITY GATES FAILED - REVIEW REQUIRED BEFORE DEPLOYMENT")
            verdict = "FAILED"
        
        print("=" * 80)
        
        return verdict
    
    def validate_api_performance(self) -> bool:
        """Validate API performance requirements"""
        performance_result = self.test_results.get("Performance", {})
        return performance_result.get("status") == "PASSED"
    
    def validate_security_tests(self) -> bool:
        """Validate security test requirements"""
        security_result = self.test_results.get("Security", {})
        return security_result.get("status") == "PASSED" and security_result.get("failed", 1) == 0
    
    def validate_business_logic(self) -> bool:
        """Validate business logic test requirements"""
        business_result = self.test_results.get("Business Logic", {})
        return business_result.get("status") == "PASSED" and business_result.get("failed", 1) == 0
    
    def validate_integration_tests(self) -> bool:
        """Validate integration test requirements"""
        integration_result = self.test_results.get("Integration Workflows", {})
        return integration_result.get("status") == "PASSED"
    
    def save_test_report(self, verdict: str):
        """Save detailed test report to file"""
        report = {
            "execution_date": datetime.now().isoformat(),
            "total_execution_time": time.time() - self.start_time,
            "verdict": verdict,
            "overall_statistics": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "skipped_tests": self.skipped_tests,
                "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            "category_results": self.test_results,
            "quality_gates": {
                "overall_success_rate": self.passed_tests / self.total_tests * 100 if self.total_tests > 0 else 0,
                "api_performance": self.validate_api_performance(),
                "security_tests": self.validate_security_tests(),
                "business_logic": self.validate_business_logic(),
                "integration_tests": self.validate_integration_tests()
            }
        }
        
        report_file = f"temporal_universe_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Detailed test report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️ Could not save test report: {e}")
    
    def run_all_tests(self, args: argparse.Namespace) -> str:
        """Run all temporal universe tests"""
        self.print_banner()
        
        # Run Docker tests if requested
        if args.docker:
            docker_success = self.run_docker_tests(args)
            if not docker_success:
                print("❌ Docker tests failed. Aborting local test execution.")
                return "FAILED"
            print()
        
        # Run each test category
        for category, info in self.test_categories.items():
            # Skip slow tests if not requested
            if args.skip_slow and "performance" in info['markers']:
                print(f"⏭️ Skipping {category} (slow tests)")
                continue
            
            result = self.run_category_tests(category, info, args)
            self.test_results[category] = result
        
        # Generate summary report
        verdict = self.generate_summary_report()
        
        # Save detailed report
        if args.save_report:
            self.save_test_report(verdict)
        
        return verdict


def main():
    """Main entry point for temporal test runner"""
    parser = argparse.ArgumentParser(description="Comprehensive Temporal Universe Test Runner")
    
    parser.add_argument("--coverage", action="store_true", help="Generate test coverage report")
    parser.add_argument("--docker", action="store_true", help="Run tests in Docker environment")
    parser.add_argument("--skip-slow", action="store_true", help="Skip performance/slow tests")
    parser.add_argument("--save-report", action="store_true", help="Save detailed JSON report")
    parser.add_argument("--category", type=str, help="Run specific test category only")
    
    args = parser.parse_args()
    
    # Change to backend directory
    if os.path.basename(os.getcwd()) != "backend":
        backend_path = os.path.join(os.getcwd(), "backend")
        if os.path.exists(backend_path):
            os.chdir(backend_path)
        else:
            print("❌ Could not find backend directory. Please run from project root.")
            sys.exit(1)
    
    # Create test runner
    runner = TemporalTestRunner()
    
    # Run specific category if requested
    if args.category:
        if args.category in runner.test_categories:
            runner.print_banner()
            result = runner.run_category_tests(args.category, runner.test_categories[args.category], args)
            runner.test_results[args.category] = result
            verdict = "PASSED" if result["status"] == "PASSED" else "FAILED"
        else:
            print(f"❌ Unknown test category: {args.category}")
            print(f"Available categories: {', '.join(runner.test_categories.keys())}")
            sys.exit(1)
    else:
        # Run all tests
        verdict = runner.run_all_tests(args)
    
    # Exit with appropriate code
    sys.exit(0 if verdict == "PASSED" else 1)


if __name__ == "__main__":
    main()