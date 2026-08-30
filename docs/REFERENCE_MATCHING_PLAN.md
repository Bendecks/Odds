# Reference matching plan

Current production evidence: 80 Bet365 events queried, 19 reference events, 6 matched H2H reference candidates.

Before adding fuzzy matching, instrument the join. For each reference observation/event record one of:
- exact event match + market price found;
- exact event match but target market missing;
- no exact event match;
- Bet365 event not queried because of call budget.

For Bet365 events, separately report whether an exact normalized reference event exists. Only after measuring name-mismatch cases should fuzzy matching be introduced, with time/home-away safeguards and tests. This avoids silently joining different fixtures.
