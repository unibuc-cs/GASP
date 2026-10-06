"""GASP v2: governed agent societies with evidence, runtime guards, typed traces.

Layout
------
gasp.core      domain-independent parts: evidence, typed actions, state, rules,
               guard, traces, metrics, statistics
gasp.domains   one module per domain (smartcity, ops); the claim of the paper
               is that only this module changes between domains
gasp.policies  procedural, naive and LLM role policies, chat backends
gasp.experiments  reproduce.py (one command for every deterministic table),
               run_grid.py (LLM grid), analyze.py (paired statistics), the
               paper table, figure and report generators

The legacy prototype behind the ESEM submission is in ``legacy/`` and is not
used by anything here.
"""

__version__ = "2.0.0"
