from pathlib import Path

import pytest

from match_eval.dataset import load_dataset
from match_eval.scoring import load_weights

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def dataset():
    return load_dataset(ROOT / "data")


@pytest.fixture(scope="session")
def weights_v1():
    return load_weights(ROOT / "weights" / "v1.json")


@pytest.fixture(scope="session")
def weights_v2():
    return load_weights(ROOT / "weights" / "v2.json")
