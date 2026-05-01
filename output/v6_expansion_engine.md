# V6 EXPANSION ENGINE — MULTI SOURCE FALLBACK

Bendix V6 har identificeret én stærk top_bet for den kommende periode, med fokus på en klar underdog-værdi i et H2H-marked med bred bookmaker-konsensus. Flere andre bets fra samme event er placeret på watchlist grundet moderate værdier eller som 'pass' ved lav værdi/konflikt.

Candidates scanned: 5 | Resolved: 4 | Conflict watchlist: 1 | Governor max top bets: 12

## DIAGNOSTICS
```json
{
  "api_errors": [],
  "quota_exhausted": false,
  "cache_used": false,
  "cache_written": true,
  "odds_api_io_used": false,
  "odds_api_io_raw_games": 0,
  "sports_found": 0,
  "sports_used": 0,
  "upcoming_raw_games": 10,
  "sport_endpoint_raw_games": 0,
  "unique_games": 10,
  "games_after_filter": 1,
  "candidate_count_before_sort": 5,
  "top_eligible_count": 0
}
```

## TOP_BETS

## WATCHLIST
1. Jannik Sinner vs Arthur Fils | h2h | Arthur Fils | None | odds 6.8 | stake 0 | role WATCHLIST | edge 25.9 | books 34 | market_weight 5.0 | score 28.43 | conf Høj | Stærkt værdi på Arthur Fils som underdog i H2H-markedet med solid bookmaker-konsensus (34 books) og høj pre_score (28.43). Prioriteres over andre markeder med færre bookmakere for samme event. Opfylder kriterierne for en stærk underdog. | Flyttet til watchlist af Top Bet Governor.
2. Jannik Sinner vs Arthur Fils | spreads | Arthur Fils | 4.5 | odds 1.83 | stake 0 | role WATCHLIST | edge 8.3 | books 9 | market_weight 0.8 | score 9.08 | conf Moderat | Moderat værdi på Fils' handicap, men H2H-markedet er den foretrukne top_bet for denne event grundet højere pre_score og flere bookmakere.
3. Jannik Sinner vs Arthur Fils | totals | Over | 21.5 | odds 2.0 | stake 0 | role WATCHLIST | edge 6.1 | books 12 | market_weight 2.2 | score 8.3 | conf Moderat | Moderat værdi i totals-markedet, men H2H-markedet er den foretrukne top_bet for denne event. Vælges over 'Under 21.5' grundet højere pre_score.

## PASS
1. Jannik Sinner vs Arthur Fils | spreads | Jannik Sinner | -4.5 | odds 2.2 | stake 0 | role Pass | edge None | books None | market_weight None | score None | conf Lav | Lav værdi og svag pre_score. Ikke stærk nok til top_bet eller watchlist.
2. Jannik Sinner vs Arthur Fils | totals | Under | 21.5 | odds 2.02 | stake 0 | role Pass | edge None | books None | market_weight None | score None | conf Lav | Konflikterer med 'Over 21.5 Games' for samme event, og 'Over' har en højere pre_score og prioriteres derfor.

