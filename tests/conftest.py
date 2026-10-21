import copy

import pytest

from eventgen.config import load_config
from eventgen.simulate import generate_match


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture(scope="session")
def match42():
    return generate_match(42, "none")


@pytest.fixture()
def fresh(match42):
    """A deep copy of a valid match that a test may corrupt."""
    return copy.deepcopy(match42)
