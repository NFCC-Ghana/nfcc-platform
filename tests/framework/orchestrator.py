"""Full Resilience Testing Platform Orchestrator."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from tests.framework.plugin import (
    PluginRegistry,
    TestContext,
    ChaosPlugin,
    SecurityPlugin,
    ObservabilityPlugin,
)
from tests.framework.analytics import FailureAnalyzer, DashboardGenerator
from tests.framework.ci.enforcer import CIEnforcer


class ResiliencePlatform:
    """Complete resilience testing platform."""

    def __init__(self, client, config: Optional[Dict[str, Any]] = None):
        self.client = client
        self.config = config or {}
        self.plugin_registry = PluginRegistry()
        self.analyzer = FailureAnalyzer()
        self.ci_enforcer = CIEnforcer(
            threshold_failures=self.config.get("threshold_failures", 0)
        )

        # Register built-in plugins
        self._register_plugins()

    def _register_plugins(self):
        """Register all available plugins."""
        self.plugin_registry.register(ChaosPlugin())
        self.plugin_registry.register(SecurityPlugin())
        self.plugin_registry.register(ObservabilityPlugin())

    def run_resilience_tests(self, base_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete resilience test suite."""
        context = TestContext(
            payload=base_payload,
            client=self.client,
            config=self.config,
            metadata={"timestamp": datetime.now().isoformat()},
        )

        # Run all plugins
        results = self.plugin_registry.run_all(context)

        # Analyze failures
        for result in results:
            if result["status"] == "failed":
                self.analyzer.add_from_response(
                    endpoint="/score",
                    response=None,  # Would need actual response
                    payload=base_payload,
                )

        # Enforce CI rules
        enforcement_result = self.ci_enforcer.evaluate(results)

        # Generate report
        report = self.analyzer.generate_report()

        return {
            "status": "passed" if enforcement_result else "failed",
            "plugin_results": results,
            "enforcement": enforcement_result,
            "report": report,
            "timestamp": datetime.now().isoformat(),
        }

    def run_continuous(self, base_payload: Dict[str, Any], interval_seconds: int = 60):
        """Run resilience tests continuously."""
        import time

        while True:
            print(f"\n🔄 Running resilience tests at {datetime.now()}")
            result = self.run_resilience_tests(base_payload)
            print(f"Status: {result['status']}")
            time.sleep(interval_seconds)

    def generate_dashboard(self) -> str:
        """Generate HTML dashboard."""
        return self.analyzer.generate_report(format="html")

    def export_results(self, filepath: str) -> None:
        """Export results to file."""
        with open(filepath, "w") as f:
            json.dump(
                {
                    "results": self.plugin_registry.get_results(),
                    "analysis": self.analyzer.summary(),
                },
                f,
                indent=2,
                default=str,
            )


# CLI interface
if __name__ == "__main__":
    import argparse
    from fastapi.testclient import TestClient
    from src.api.main import app

    parser = argparse.ArgumentParser(description="Resilience Testing Platform")
    parser.add_argument("--threshold", type=int, default=0, help="Failure threshold")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--dashboard", action="store_true", help="Generate dashboard")
    parser.add_argument("--export", type=str, help="Export results to file")

    args = parser.parse_args()

    client = TestClient(app)
    platform = ResiliencePlatform(client, config={"threshold_failures": args.threshold})

    if args.dashboard:
        print(platform.generate_dashboard())
    elif args.continuous:
        platform.run_continuous({})
    else:
        result = platform.run_resilience_tests({})
        print(json.dumps(result, indent=2, default=str))

    if args.export:
        platform.export_results(args.export)
        print(f"✅ Results exported to {args.export}")
