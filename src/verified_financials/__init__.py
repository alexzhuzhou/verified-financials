"""Sentinel — verification, borrowing base, and FCCR engines.

A demo platform that ingests messy financial data into a provenance-tracked
fact store, then runs three engines over it:

* verification / tie-out  — flag figures that do not reconcile
* borrowing base          — apply facility eligibility rules -> bank-ready certificate
* FCCR covenant           — compute TTM Fixed Charge Coverage Ratio + early warning
"""

__version__ = "0.1.0"
