"""Failure analytics and dashboard generation."""

import json
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class FailureEvent:
    """Record of a failure event."""
    endpoint: str
    error_type: str
    error_code: int
    payload: Dict[str, Any]
    timestamp: datetime
    trace_id: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


class FailureAnalyzer:
    """Analyze failure patterns and generate insights."""
    
    def __init__(self):
        self.events: List[FailureEvent] = []
    
    def add(self, event: FailureEvent) -> None:
        """Add a failure event."""
        self.events.append(event)
    
    def add_from_response(self, endpoint: str, response, payload: Dict[str, Any]) -> None:
        """Create and add failure event from response."""
        event = FailureEvent(
            endpoint=endpoint,
            error_type=response.status_code,
            error_code=response.status_code,
            payload=payload,
            timestamp=datetime.now(),
            response=response.json() if response.text else None,
        )
        self.events.append(event)
    
    def summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not self.events:
            return {"total_events": 0}
        
        return {
            "total_events": len(self.events),
            "by_endpoint": Counter([e.endpoint for e in self.events]),
            "by_error_code": Counter([e.error_code for e in self.events]),
            "by_error_type": Counter([e.error_type for e in self.events]),
            "time_range": {
                "first": min(e.timestamp for e in self.events),
                "last": max(e.timestamp for e in self.events),
            },
        }
    
    def top_failures(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N failure patterns."""
        patterns = defaultdict(list)
        for event in self.events:
            key = f"{event.endpoint}:{event.error_code}"
            patterns[key].append(event)
        
        sorted_patterns = sorted(
            patterns.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        return [
            {
                "pattern": pattern,
                "count": len(events),
                "sample": asdict(events[0]) if events else None,
            }
            for pattern, events in sorted_patterns[:n]
        ]
    
    def failure_heatmap(self) -> Dict[str, int]:
        """Generate failure heatmap data."""
        heatmap = defaultdict(int)
        for event in self.events:
            heatmap[f"{event.endpoint}"] += 1
        return dict(heatmap)
    
    def root_cause_analysis(self) -> Dict[str, Any]:
        """Simple root cause analysis."""
        causes = {
            "MODEL_ERROR": 0,
            "VALIDATION_ERROR": 0,
            "RATE_LIMIT": 0,
            "TIMEOUT": 0,
            "IO_ERROR": 0,
        }
        
        for event in self.events:
            if event.error_code >= 500:
                causes["MODEL_ERROR"] += 1
            elif event.error_code == 422:
                causes["VALIDATION_ERROR"] += 1
            elif event.error_code == 429:
                causes["RATE_LIMIT"] += 1
            elif event.error_code == 504:
                causes["TIMEOUT"] += 1
        
        return causes
    
    def generate_report(self, format: str = "json") -> str:
        """Generate comprehensive report."""
        report = {
            "summary": self.summary(),
            "top_failures": self.top_failures(5),
            "heatmap": self.failure_heatmap(),
            "root_causes": self.root_cause_analysis(),
            "timestamp": datetime.now().isoformat(),
        }
        
        if format == "json":
            return json.dumps(report, indent=2, default=str)
        elif format == "html":
            return self._generate_html_report(report)
        return str(report)
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML dashboard."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resilience Test Dashboard</title>
            <style>
                body {{ font-family: Arial; margin: 20px; }}
                .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .heatmap {{ margin: 20px 0; }}
                .bar {{ background: #4CAF50; color: white; padding: 5px; margin: 2px; }}
                .critical {{ background: #f44336; }}
                .warning {{ background: #ff9800; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Resilience Test Dashboard</h1>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Events: {report['summary']['total_events']}</p>
                <p>Time Range: {report['summary'].get('time_range', {}).get('first', 'N/A')} to {report['summary'].get('time_range', {}).get('last', 'N/A')}</p>
            </div>
            
            <h2>Failure Heatmap</h2>
            <div class="heatmap">
                {''.join(f'<div class="bar" style="width: {min(100, count * 10)}%">{endpoint}: {count}</div>' for endpoint, count in report['heatmap'].items())}
            </div>
            
            <h2>Top Failures</h2>
            <table>
                <tr><th>Pattern</th><th>Count</th></tr>
                {''.join(f'<tr><td>{f["pattern"]}</td><td>{f["count"]}</td></tr>' for f in report['top_failures'])}
            </table>
            
            <h2>Root Causes</h2>
            <table>
                <tr><th>Cause</th><th>Count</th></tr>
                {''.join(f'<tr><td>{cause}</td><td>{count}</td></tr>' for cause, count in report['root_causes'].items() if count > 0)}
            </table>
        </body>
        </html>
        """


class DashboardGenerator:
    """Generate interactive dashboards."""
    
    @staticmethod
    def generate_heatmap(failures: Dict[str, int]) -> str:
        """Generate failure heatmap visualization."""
        import json
        return json.dumps(failures)
    
    @staticmethod
    def generate_timeline(events: List[FailureEvent]) -> str:
        """Generate timeline visualization data."""
        timeline = []
        for event in events:
            timeline.append({
                "timestamp": event.timestamp.isoformat(),
                "endpoint": event.endpoint,
                "error": event.error_code,
            })
        return json.dumps(timeline)
