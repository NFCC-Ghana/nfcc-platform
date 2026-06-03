from src.models.dam_spillage import compute_spillage_probability


def test_probability_range():
    result = compute_spillage_probability(100, 80, 200)
    assert 0 <= result <= 100


def test_high_risk():
    result = compute_spillage_probability(200, 95, 400)
    assert result > 70

def test_extreme_conditions():
    result = compute_spillage_probability(500, 50, 1000)
    assert result > 70

def test_zero_conditions():
    result = compute_spillage_probability(0, 0, 0)
    assert result == 0