"""EvoTank headless simulation prototype (throwaway validation code).

Implements the core simulation from docs/DESIGN.md well enough to answer the two
riskiest numeric questions before any engine is chosen:
  1. Does the metabolism/reproduction tuning produce a *slow burn* (§3, §11.1)?
  2. Does the cohort idle model track the live agent sim (§6, §11.2)?

This is NOT the shipping codebase — module seams mirror DESIGN §10 only so the
validated logic maps cleanly into the real engine later.
"""
