"""Community Report Classifier - Validates citizen flood reports."""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hackathon.classifier")


@dataclass
class ClassifiedReport:
    """Classified community flood report."""

    text: str
    severity: str
    category: str
    confidence: float
    is_flood_related: bool
    keywords_found: List[str]


class CommunityReportClassifier:
    """Classify citizen WhatsApp reports into structured flood intelligence."""

    # Severity keywords
    SEVERITY_KEYWORDS = {
        "EXTREME": [
            "urgent",
            "emergency",
            "help",
            "danger",
            "evacuate",
            "life threatening",
            "fatal",
        ],
        "HIGH": [
            "waist deep",
            "chest deep",
            "homes flooded",
            "cars submerged",
            "road blocked",
        ],
        "MODERATE": [
            "ankle deep",
            "knee deep",
            "water entering",
            "flooding",
            "water rising",
        ],
        "LOW": ["drain blocked", "water logging", "puddles", "overflowing"],
    }

    # Category keywords
    CATEGORY_KEYWORDS = {
        "road_flooding": ["road", "street", "highway", "blocked", "pass", "bridge"],
        "property_damage": ["home", "house", "shop", "property", "building", "wall"],
        "drainage_issue": ["drain", "gutter", "channel", "blocked", "choked"],
        "river_flooding": ["river", "stream", "bank", "overflow", "water level"],
        "general_flood": ["flood", "water", "rain", "submerged", "inundated"],
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for keyword matching."""
        self.severity_patterns = {
            level: re.compile("|".join(keywords), re.IGNORECASE)
            for level, keywords in self.SEVERITY_KEYWORDS.items()
        }
        self.category_patterns = {
            category: re.compile("|".join(keywords), re.IGNORECASE)
            for category, keywords in self.CATEGORY_KEYWORDS.items()
        }

    def classify(self, text: str, location: Optional[str] = None) -> ClassifiedReport:
        """Classify a community report."""
        text_lower = text.lower()

        # Determine severity
        severity, severity_confidence = self._detect_severity(text_lower)

        # Determine category
        category, category_confidence = self._detect_category(text_lower)

        # Extract keywords found
        keywords = self._extract_keywords(text_lower)

        # Calculate overall confidence
        confidence = (severity_confidence + category_confidence) / 2

        # Determine if flood-related
        is_flood_related = len(keywords) > 0 or severity != "LOW"

        return ClassifiedReport(
            text=text,
            severity=severity,
            category=category,
            confidence=round(confidence, 2),
            is_flood_related=is_flood_related,
            keywords_found=keywords,
        )

    def _detect_severity(self, text: str) -> Tuple[str, float]:
        """Detect severity level from text."""
        for level, pattern in self.severity_patterns.items():
            if pattern.search(text):
                # Calculate confidence based on match strength
                matches = len(pattern.findall(text))
                confidence = min(0.95, 0.6 + (matches * 0.1))
                return level, confidence

        return "LOW", 0.5

    def _detect_category(self, text: str) -> Tuple[str, float]:
        """Detect category from text."""
        best_category = "general_flood"
        best_confidence = 0.3

        for category, pattern in self.category_patterns.items():
            if pattern.search(text):
                matches = len(pattern.findall(text))
                confidence = min(0.9, 0.5 + (matches * 0.1))
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_category = category

        return best_category, best_confidence

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        keywords = []
        for level, pattern in self.severity_patterns.items():
            if pattern.search(text):
                keywords.append(level.lower())

        for category, pattern in self.category_patterns.items():
            if pattern.search(text):
                keywords.append(category.replace("_", " "))

        return keywords[:5]  # Limit to 5 keywords

    def format_for_dashboard(self, report: ClassifiedReport) -> Dict[str, Any]:
        """Format classified report for dashboard display."""
        severity_color = {
            "EXTREME": "red",
            "HIGH": "orange",
            "MODERATE": "yellow",
            "LOW": "green",
        }.get(report.severity, "gray")

        return {
            "text": report.text[:100] + ("..." if len(report.text) > 100 else ""),
            "severity": report.severity,
            "severity_color": severity_color,
            "category": report.category.replace("_", " ").title(),
            "confidence": f"{int(report.confidence * 100)}%",
            "is_flood_related": report.is_flood_related,
            "keywords": ", ".join(report.keywords_found[:3]),
        }


# Singleton instance
classifier = CommunityReportClassifier()
