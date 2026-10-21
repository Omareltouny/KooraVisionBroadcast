"""Synthetic football event generator (fictional league, seeded, story injection)."""
from .schema import GENERATOR_VERSION as __version__  # noqa: F401
from .replay import areplay, replay  # noqa: E402,F401
from .simulate import generate_league, generate_match  # noqa: E402,F401
