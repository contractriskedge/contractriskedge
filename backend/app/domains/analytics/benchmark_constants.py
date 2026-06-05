"""
Benchmark constants for Executive Dashboard analytics.

These define target values for operational benchmarks.
Adjust as organizational standards evolve.
"""

from __future__ import annotations

from typing import Final

# ── Cycle Time Benchmark ───────────────────────────────────────────
# Target: reviews should complete within this many days.

BENCHMARK_CYCLE_TIME_DAYS: Final[float] = 5.0

# ── SLA Benchmark ──────────────────────────────────────────────────
# Target: percentage of reviews meeting SLA deadlines.

BENCHMARK_SLA_PCT: Final[float] = 95.0

# ── Reviewer Load Benchmark ────────────────────────────────────────
# Target: maximum active reviews per reviewer before flagged as overloaded.

BENCHMARK_REVIEWER_LOAD: Final[int] = 5
