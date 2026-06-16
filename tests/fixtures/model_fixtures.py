"""Model-related pytest fixtures for NFCC tests."""

import pytest
import numpy as np


class DummyFloodRiskModel:
    """Small test model with a predict method."""

    def predict(self, data):
        """Return simple deterministic risk scores for tests."""

        if hasattr(data, "__len__"):
            return np.full(len(data), 50.0)

        return np.array([50.0])


@pytest.fixture
def trained_model():
    """Return a lightweight trained-model substitute for tests."""

    return DummyFloodRiskModel()