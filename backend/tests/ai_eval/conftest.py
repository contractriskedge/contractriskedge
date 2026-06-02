"""pytest configuration for AI evaluation tests."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register AI evaluation command-line options."""
    parser.addoption(
        "--eval-suite",
        action="store",
        default="smoke",
        choices=["smoke", "full", "regression"],
        help="AI evaluation suite to run: smoke (default), full, regression",
    )
    parser.addoption(
        "--eval-report",
        action="store",
        default=None,
        help="Path to write evaluation report JSON",
    )
    parser.addoption(
        "--eval-contract-types",
        action="store",
        default=None,
        help="Comma-separated list of contract types to evaluate",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for AI evaluation tests."""
    config.addinivalue_line("markers", "ai_eval: AI evaluation test (golden contract validation)")
    config.addinivalue_line("markers", "ai_smoke: Quick smoke test (single contract)")
    config.addinivalue_line("markers", "ai_regression: Full regression suite")
    config.addinivalue_line("markers", "ai_hallucination: Hallucination detection tests")
