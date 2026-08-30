# Current bottleneck: cross-provider coverage

The 2026-08-30 post-PR4 run showed 80 queried Bet365 events but only 19 events in the configured The Odds API reference leagues/window, yielding 57 strong reference observations and only 6 Bet365/reference matches.

Therefore the next optimization target is not loosening final value/risk gates. It is increasing the fraction of Bet365 events/markets that receive defensible independent reference probabilities.

Work should focus on:
1. event-name/team normalization and fuzzy-but-safe cross-provider matching;
2. measuring exact unmatched reasons (sport/league absent, event absent, name mismatch, market mismatch, outside time window);
3. adding totals/spreads reference support only with explicit API-credit accounting;
4. broadening sports/leagues based on active provider coverage rather than a hard-coded football list;
5. retaining all Bet365 observations even when no reference exists yet.
