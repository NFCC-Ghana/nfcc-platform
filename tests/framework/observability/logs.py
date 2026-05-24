"""Log validation utilities."""

import logging
import re
from typing import List, Optional, Pattern


class LogValidator:
    """Validate log emissions."""

    def __init__(self, caplog):
        self.caplog = caplog
        self.records = []
    
    def capture(self, func, *args, **kwargs):
        """Capture logs during function execution."""
        with self.caplog.at_level(logging.INFO):
            result = func(*args, **kwargs)
            self.records = self.caplog.records
            return result
    
    def assert_contains(self, text: str, level: Optional[str] = None, regex: bool = False):
        """Assert log contains expected text."""
        pattern = re.compile(text) if regex else None
        
        for record in self.records:
            message = record.getMessage()
            if regex:
                if pattern.search(message):
                    if level is None or record.levelname == level:
                        return True
            else:
                if text in message:
                    if level is None or record.levelname == level:
                        return True
        
        raise AssertionError(f"Log not found: '{text}' (level: {level})")
    
    def assert_count(self, text: str, expected_count: int, level: Optional[str] = None):
        """Assert specific number of log entries."""
        count = 0
        for record in self.records:
            if text in record.getMessage():
                if level is None or record.levelname == level:
                    count += 1
        
        assert count == expected_count, f"Expected {expected_count} entries, got {count}"
    
    def assert_error_logged(self, error_text: str):
        """Assert error was logged."""
        return self.assert_contains(error_text, level="ERROR")
    
    def assert_warning_logged(self, warning_text: str):
        """Assert warning was logged."""
        return self.assert_contains(warning_text, level="WARNING")
    
    def assert_info_logged(self, info_text: str):
        """Assert info was logged."""
        return self.assert_contains(info_text, level="INFO")
    
    def get_logs_by_level(self, level: str) -> List[str]:
        """Get all logs at specific level."""
        return [r.getMessage() for r in self.records if r.levelname == level]
    
    def clear(self):
        """Clear captured logs."""
        self.records = []
        self.caplog.clear()
