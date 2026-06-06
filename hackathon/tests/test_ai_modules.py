"""Tests for hackathon AI modules."""

from hackathon.ai.flood_explainer import explainer
from hackathon.ai.community_classifier import classifier
from hackathon.ai.impact_estimator import impact_estimator
from hackathon.ai.timeline_predictor import timeline_predictor


class TestFloodExplainer:
    def test_explain_high_risk(self):
        features = {"precipitation": 0.9, "roll_3d": 0.7}
        result = explainer.explain(85.0, features)
        assert result.risk_level in ["EXTREME", "CRITICAL", "HIGH"]
        assert result.confidence > 0.5
        assert len(result.primary_factors) > 0

    def test_explain_low_risk(self):
        features = {"precipitation": 0.1}
        result = explainer.explain(15.0, features)
        assert result.risk_level == "LOW"

    def test_format_whatsapp(self):
        features = {"precipitation": 0.8}
        result = explainer.explain(75.0, features)
        whatsapp_msg = explainer.format_for_whatsapp(result)
        assert "FLOOD ALERT" in whatsapp_msg


class TestCommunityClassifier:
    def test_classify_flood_report(self):
        result = classifier.classify("Water has entered our homes on Abeka Road")
        assert result.is_flood_related is True
        assert result.severity in ["EXTREME", "HIGH", "MODERATE", "LOW"]

    def test_classify_non_flood(self):
        result = classifier.classify("The weather is nice today")
        assert result.is_flood_related is False

    def test_severity_detection(self):
        result = classifier.classify("URGENT! Emergency! Water rising fast!")
        assert result.severity in ["EXTREME", "HIGH"]


class TestImpactEstimator:
    def test_estimate_high_risk(self):
        result = impact_estimator.estimate(85.0, "Accra Central")
        assert result.population_exposed > 0
        assert result.schools_affected > 0
        assert result.confidence > 0.5

    def test_estimate_low_risk(self):
        result = impact_estimator.estimate(15.0, "Tamale")
        assert result.population_exposed < 50000
        assert result.confidence < 0.8


class TestTimelinePredictor:
    def test_predict_timeline(self):
        result = timeline_predictor.predict(75.0)
        assert "day1" in result
        assert "day3" in result
        assert "day7" in result

    def test_trend_detection(self):
        timeline = {"day1": 80, "day3": 60, "day7": 40}
        trend = timeline_predictor.get_trend(timeline)
        assert trend == "decreasing"
