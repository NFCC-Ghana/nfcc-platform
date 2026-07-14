"""Flood Explainability Engine - Converts ML outputs to plain English."""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("hackathon.explainer")


@dataclass
class ExplanationResult:
    """Human-readable flood explanation."""

    risk_level: str
    confidence: float
    primary_factors: List[str]
    action_required: str
    detailed_explanation: str


class FloodExplainer:
    """Convert SHAP values and model outputs into plain English explanations."""

    def __init__(self):
        self.risk_thresholds = {
            "EXTREME": (85, 101),
            "CRITICAL": (70, 85),
            "HIGH": (50, 70),
            "MODERATE": (30, 50),
            "LOW": (0, 30),
        }

        self.action_map = {
            "EXTREME": "EVACUATE IMMEDIATELY - Seek higher ground",
            "CRITICAL": "PREPARE TO EVACUATE - Monitor water levels",
            "HIGH": "TAKE PRECAUTIONS - Avoid low-lying areas",
            "MODERATE": "STAY AWARE - Monitor local conditions",
            "LOW": "NORMAL OPERATIONS - Stay informed",
        }

    def explain(
        self, risk_score: float, features: Dict[str, float]
    ) -> ExplanationResult:
        """Generate human-readable explanation for a flood risk prediction."""

        # Determine risk level
        risk_level = self._get_risk_level(risk_score)
        confidence = self._calculate_confidence(risk_score, features)

        # Identify primary factors
        primary_factors = self._identify_factors(features)

        # Generate detailed explanation
        detailed = self._generate_detailed_explanation(
            risk_level, features, primary_factors
        )

        return ExplanationResult(
            risk_level=risk_level,
            confidence=confidence,
            primary_factors=primary_factors,
            action_required=self.action_map.get(risk_level, "Monitor conditions"),
            detailed_explanation=detailed,
        )

    def _get_risk_level(self, score: float) -> str:
        for level, (low, high) in self.risk_thresholds.items():
            if low <= score < high:
                return level
        return "LOW"

    def _calculate_confidence(self, score: float, features: Dict[str, float]) -> float:
        """Calculate confidence based on feature agreement."""
        if not features:
            return 0.5

        # Higher confidence when extreme features align
        max_feature = max(features.values()) if features else 0
        base_confidence = min(0.95, 0.5 + (score / 200))

        # Adjust based on feature strength
        if max_feature > 0.7:
            base_confidence = min(0.98, base_confidence + 0.1)

        return round(base_confidence, 2)

    def _identify_factors(self, features: Dict[str, float]) -> List[str]:
        """Identify the top contributing factors."""
        if not features:
            return ["Insufficient data for analysis"]

        sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)

        factor_map = {
            "precipitation": "Heavy rainfall",
            "roll_3d": "Sustained rainfall over 3 days",
            "roll_7d": "Extended wet period",
            "cumulative": "High cumulative seasonal rainfall",
            "z_score": "Rainfall significantly above average",
            "river_discharge": "Elevated river levels",
            "community_reports": "Multiple community flood reports",
        }

        factors = []
        for key, value in sorted_features[:3]:
            if value > 0.3:  # Only include significant factors
                factor_name = factor_map.get(key, key.replace("_", " ").title())
                factors.append(f"{factor_name} ({int(value * 100)}% contribution)")

        return factors if factors else ["Standard seasonal conditions"]

    def _generate_detailed_explanation(
        self, risk_level: str, features: Dict[str, float], factors: List[str]
    ) -> str:
        """Generate detailed narrative explanation."""
        if not factors or risk_level == "LOW":
            msg = (
                f"The current conditions show {risk_level} flood risk. No immediate "
                "action is required, but stay informed of weather updates."
            )
            return msg

        factors_text = ", ".join(factors[:-1]) + (
            f" and {factors[-1]}" if len(factors) > 1 else factors[0]
        )

        return (
            f"Flood risk is {risk_level.lower()} due to {factors_text}. "
            f"{self.action_map.get(risk_level, 'Monitor conditions.')}"
        )

    def format_for_whatsapp(self, explanation: ExplanationResult) -> str:
        """Format explanation for WhatsApp message."""
        emoji_map = {
            "EXTREME": "💀",
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MODERATE": "🟡",
            "LOW": "🟢",
        }

        return f"""
{emoji_map.get(explanation.risk_level, '⚠️')} *FLOOD ALERT*

*Risk Level:* {explanation.risk_level}
*Confidence:* {int(explanation.confidence * 100)}%

*Why?*
{explanation.detailed_explanation}

*Action:* {explanation.action_required}

Stay safe. Report flooding via WhatsApp.
"""

    def format_for_dashboard(self, explanation: ExplanationResult) -> Dict[str, Any]:
        """Format explanation for dashboard display."""
        return {
            "risk_level": explanation.risk_level,
            "risk_score": None,  # Will be filled by caller
            "confidence": explanation.confidence,
            "primary_factors": explanation.primary_factors,
            "action_required": explanation.action_required,
            "detailed_explanation": explanation.detailed_explanation,
        }


# Singleton instance
explainer = FloodExplainer()
