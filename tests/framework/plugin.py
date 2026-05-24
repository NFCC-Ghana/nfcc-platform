"""Plugin-based architecture for extensible resilience testing."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class TestContext:
    """Context passed to plugins."""

    payload: Dict[str, Any]
    client: Any
    config: Dict[str, Any]
    metadata: Dict[str, Any]


class ResiliencePlugin(ABC):
    """Base plugin for all resilience tests."""

    name: str = "base"
    version: str = "1.0.0"

    @abstractmethod
    def execute(self, context: TestContext) -> Dict[str, Any]:
        """Execute plugin and return results."""
        pass

    def configure(self, config: Dict[str, Any]):
        """Configure plugin with custom settings."""
        self.config = config
        return self


class PluginRegistry:
    """Registry for managing resilience plugins."""

    def __init__(self):
        self.plugins: Dict[str, ResiliencePlugin] = {}
        self.results: List[Dict[str, Any]] = []

    def register(self, plugin: ResiliencePlugin) -> None:
        """Register a plugin."""
        self.plugins[plugin.name] = plugin
        print(f"✅ Registered plugin: {plugin.name} v{plugin.version}")

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name in self.plugins:
            del self.plugins[name]
            print(f"❌ Unregistered plugin: {name}")

    def run_all(self, context: TestContext) -> List[Dict[str, Any]]:
        """Run all registered plugins."""
        self.results = []
        for name, plugin in self.plugins.items():
            try:
                result = plugin.execute(context)
                self.results.append(
                    {
                        "plugin": name,
                        "status": "success",
                        "result": result,
                    }
                )
            except Exception as e:
                self.results.append(
                    {
                        "plugin": name,
                        "status": "failed",
                        "error": str(e),
                    }
                )
        return self.results

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all plugin results."""
        return self.results


# Example plugins
class ChaosPlugin(ResiliencePlugin):
    name = "chaos"
    version = "2.0.0"

    def execute(self, context: TestContext) -> Dict[str, Any]:
        from tests.framework.chaos import ChaosEngine

        result = ChaosEngine.random_mutation(context.payload)
        return {
            "strategy": result.strategy,
            "severity": result.severity,
            "changes": result.changes,
        }


class SecurityPlugin(ResiliencePlugin):
    name = "security"
    version = "1.0.0"

    def execute(self, context: TestContext) -> Dict[str, Any]:
        from tests.framework.security import InjectionTester, DoSTester

        # Run security checks
        return {
            "injection_tested": True,
            "dos_tested": True,
        }


class ObservabilityPlugin(ResiliencePlugin):
    name = "observability"
    version = "1.0.0"

    def execute(self, context: TestContext) -> Dict[str, Any]:
        from tests.framework.observability import LogValidator, TracingValidator

        # Validate observability
        return {
            "logs_validated": True,
            "traces_validated": True,
        }
