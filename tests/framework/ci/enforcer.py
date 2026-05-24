"""CI/CD enforcement layer."""

import os
import sys
from typing import Dict, Any, List


class CIEnforcer:
    """Enforce resilience quality gates in CI."""
    
    def __init__(self, threshold_failures: int = 0, coverage_threshold: float = 85.0):
        self.threshold_failures = threshold_failures
        self.coverage_threshold = coverage_threshold
    
    def evaluate(self, results: List[Dict[str, Any]]) -> bool:
        """Evaluate results against thresholds."""
        failures = [r for r in results if r.get("status") == "failed"]
        
        if len(failures) > self.threshold_failures:
            print(f"❌ CI BLOCKED: {len(failures)} resilience failures detected (threshold: {self.threshold_failures})")
            return False
        
        print(f"✅ CI PASSED: {len(failures)} failures within threshold")
        return True
    
    def evaluate_coverage(self, coverage_report: Dict[str, float]) -> bool:
        """Evaluate coverage thresholds."""
        total_coverage = coverage_report.get("total", 0)
        
        if total_coverage < self.coverage_threshold:
            print(f"❌ CI BLOCKED: Coverage {total_coverage}% below threshold {self.coverage_threshold}%")
            return False
        
        print(f"✅ Coverage {total_coverage}% meets threshold {self.coverage_threshold}%")
        return True
    
    def block_deployment(self, reason: str) -> None:
        """Block deployment with reason."""
        print(f"🚫 DEPLOYMENT BLOCKED: {reason}")
        sys.exit(1)


# GitHub Actions integration
def github_action_main():
    """Entry point for GitHub Actions."""
    import json
    import subprocess
    
    # Run resilience tests
    result = subprocess.run(
        ["pytest", "tests/framework", "--json", "--report-log=resilience.json"],
        capture_output=True
    )
    
    # Parse results
    try:
        with open("resilience.json") as f:
            results = json.load(f)
    except:
        results = {"failed": 1 if result.returncode != 0 else 0}
    
    # Enforce
    enforcer = CIEnforcer(threshold_failures=0)
    if not enforcer.evaluate([{"status": "failed"} if result.returncode != 0 else {}]):
        enforcer.block_deployment("Resilience tests failed")


if __name__ == "__main__":
    github_action_main()
