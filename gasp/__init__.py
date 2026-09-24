"""GASP v2: governed agent societies with evidence, runtime guards, typed traces.

Layout
------
gasp.core      domain-independent parts: evidence, typed actions, state, rules,
               guard, traces, metrics, statistics
gasp.domains   one module per domain (smartcity now, ops later); the claim of
               the paper is that only this module changes between domains
gasp.policies  procedural, naive, oracle and LLM role policies
gasp.experiments  reproduce.py (one command for every table), run_grid.py,
               analyze.py

The legacy prototype used for the ESEM submission stays in ``smartcity_gasp``
and is not used by anything here.
"""

__version__ = "2.0.0-dev"
