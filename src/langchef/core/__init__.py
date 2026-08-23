"""Deterministic core: statistics, calibration, metrics, and the agent contract.

Boundary rule (DECISIONS.md #5): this package imports nothing from
``langchef.judge``, ``langchef.connect`` or ``langchef.packs``. Enforced by
``tests/test_boundaries.py``, so every number in the product is testable with
no API key and no network.
"""
