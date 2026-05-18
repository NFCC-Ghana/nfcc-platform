"""Unit tests — Rainfall classification function."""


def classify_rainfall(value):
    if value >= 30:
        return "Extreme"
    elif value >= 15:
        return "High"
    elif value >= 5:
        return "Moderate"
    elif value > 0:
        return "Light"
    return "Dry"


class TestRainfallClassification:
    def test_dry_day(self):
        assert classify_rainfall(0.0) == "Dry"

    def test_trace_rain(self):
        assert classify_rainfall(0.001) == "Light"

    def test_light_rain(self):
        assert classify_rainfall(1.0) == "Light"

    def test_moderate_rain(self):
        assert classify_rainfall(10.0) == "Moderate"

    def test_high_rain(self):
        assert classify_rainfall(20.0) == "High"

    def test_extreme_rain(self):
        assert classify_rainfall(50.0) == "Extreme"

    def test_boundary_moderate(self):
        assert classify_rainfall(5.0) == "Moderate"

    def test_boundary_high(self):
        assert classify_rainfall(15.0) == "High"

    def test_boundary_extreme(self):
        assert classify_rainfall(30.0) == "Extreme"

    def test_integer_input(self):
        assert classify_rainfall(30) == "Extreme"

    def test_returns_string(self):
        assert isinstance(classify_rainfall(10.0), str)

    def test_all_valid_classes(self):
        valid = {"Dry", "Light", "Moderate", "High", "Extreme"}
        inputs = [0, 0.1, 5, 15, 30, 100]
        for val in inputs:
            assert classify_rainfall(val) in valid
