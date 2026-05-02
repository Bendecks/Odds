# V10 ADAPTIVE FEEDBACK ACTIVE

Activated: 2026-05-02T17:38:50.956110+00:00 | feedback patterns: 0 | adjustments applied: 0

No V9 feedback data yet. V10 is active but neutral until enough settled bets exist.

# V7 MULTI-SPORT ENGINE — RISK GOVERNOR

CACHE/STale odds used. V7 Risk Governor: Picks prioritized by high pre_score and bookmaker count (ideally >=30) for strong singles. Risk balance maintained by limiting MMA and longshot picks, relegating them to the watchlist with specific cautionary notes. Max 1 pick per event rule is strictly observed across both top bets and watchlist.

Candidates scanned: 366 | Resolved: 238 | Conflict watchlist: 128 | Governor max top bets: 20 | Timezone: Europe/Copenhagen

## RISK COUNTS
```json
{
  "sport": {
    "icehockey": 2,
    "soccer": 1
  },
  "longshot": 0,
  "high_odds": 3,
  "low_books": 0,
  "totals": 0,
  "spreads": 0
}
```

## DIAGNOSTICS
```json
{
  "api_errors": [
    {
      "label": "theodds:soccer_epl",
      "error": "401 {\"message\":\"Usage quota has been reached. See usage plans at https://the-odds-api.com\",\"error_code\":\"OUT_OF_USAGE_CREDITS\",\"details_url\":\"https://the-odds-api.com/liveapi/guides/v4/api-error-codes.html#out-of-usage-credits\"}\n"
    }
  ],
  "quota_exhausted": true,
  "cache_used": true,
  "cache_written": false,
  "odds_api_io_used": false,
  "odds_api_io_raw_games": 0,
  "odds_api_io_events": 229,
  "odds_api_io_odds_calls": 16,
  "theodds_sports_used": 8,
  "theodds_sport_games": 0,
  "unique_games": 157,
  "games_after_filter": 67,
  "candidate_count_before_sort": 366,
  "top_eligible_count": 124,
  "gemini_shortlist": 30,
  "gemini_timeout_guard": true,
  "risk_governor": true,
  "risk_moved_to_watchlist": 0
}
```

## TOP_BETS
1. Carolina Hurricanes vs Philadelphia Flyers | start 2026-05-03 02:10 | sport icehockey_nhl | h2h | Philadelphia Flyers | None | odds 3.9 | stake 2 | role PRIMARY | edge 19.4 | books 32 | score 23.65 | conf High | Highest pre_score with excellent edge and high bookmaker consensus (32 books). Odds are good for value without being an extreme longshot.
2. Tampa Bay Lightning vs Montréal Canadiens | start 2026-05-04 00:10 | sport icehockey_nhl | h2h | Montréal Canadiens | None | odds 3.24 | stake 2 | role PRIMARY | edge 16.8 | books 32 | score 21.76 | conf High | Very high pre_score, strong edge, and robust market support (32 books). Reasonable odds for a solid value pick.
3. Levante vs CA Osasuna | start 2026-05-08 21:00 | sport soccer_spain_la_liga | h2h | CA Osasuna | None | odds 3.05 | stake 2 | role PRIMARY | edge 10.9 | books 31 | score 15.91 | conf High | High pre_score, good edge, and strong market support (31 books) for a mainstream soccer event. Favorable odds.

## WATCHLIST
1. Joel Alvarez vs Bryce Logan | start 2026-05-03 02:00 | sport mma_mixed_martial_arts | h2h | Bryce Logan | None | odds 3.5 | stake 0 | role WATCHLIST | edge 20.7 | books 6 | score 22.89 | conf Medium | Exceptionally high pre_score and edge, but cautious due to very low bookmaker count (6 books) and MMA sport, which carries higher inherent variance.
2. Colorado Avalanche vs Minnesota Wild | start 2026-05-04 03:10 | sport icehockey_nhl | h2h | Minnesota Wild | None | odds 3.5 | stake 0 | role WATCHLIST | edge 12.0 | books 30 | score 16.2 | conf Medium | Solid pre_score, good edge, and high bookmaker support (30 books). A strong candidate that narrowly missed top bets.
3. Bournemouth vs Crystal Palace | start 2026-05-03 15:00 | sport soccer_epl | h2h | Crystal Palace | None | odds 5.6 | stake 0 | role WATCHLIST | edge 12.0 | books 40 | score 14.5 | conf Medium | Good pre_score and excellent market support (40 books), but categorized as a longshot due to high odds. Worth monitoring for potential upsets.
4. VfB Stuttgart vs Bayer Leverkusen | start 2026-05-09 15:30 | sport soccer_germany_bundesliga | h2h | Bayer Leverkusen | None | odds 3.25 | stake 0 | role WATCHLIST | edge 8.3 | books 31 | score 13.33 | conf Medium | Good pre_score, solid edge, and strong bookmaker presence (31 books). A reliable value pick for a popular soccer league.
5. Elche CF vs Alavés | start 2026-05-09 14:00 | sport soccer_spain_la_liga | h2h | Alavés | None | odds 3.4 | stake 0 | role WATCHLIST | edge 7.9 | books 30 | score 12.94 | conf Medium | Decent pre_score, fair edge, and good bookmaker support (30 books). Another consistent pick in a mainstream soccer league.
6. Cleveland Cavaliers vs Toronto Raptors | start 2026-05-04 01:40 | sport basketball_nba | h2h | Toronto Raptors | None | odds 3.81 | stake 0 | role WATCHLIST | edge 7.3 | books 37 | score 11.52 | conf Medium | Good pre_score and strong bookmaker support (37 books) for an NBA pick, providing decent value in basketball.
7. Athletics vs Cleveland Guardians | start 2026-05-02 22:06 | sport baseball_mlb | h2h | Cleveland Guardians | None | odds 2.25 | stake 0 | role WATCHLIST | edge 6.1 | books 36 | score 11.13 | conf Medium | Solid pre_score, good books (36 books), and lower odds make this a relatively safer value pick in baseball.

## PASS
1. Augsburg vs Borussia Monchengladbach | start  | sport None | h2h | Borussia Monchengladbach | None | odds 3.07 | stake 0 | role Pass | edge None | books None | score None | conf Low | Slightly lower pre_score and edge compared to higher-ranked watchlist picks.
2. Borussia Monchengladbach vs Borussia Dortmund | start  | sport None | h2h | Borussia Monchengladbach | None | odds 3.95 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books but edge is relatively lower for the higher odds compared to stronger picks.
3. SC Freiburg vs VfL Wolfsburg | start  | sport None | h2h | SC Freiburg | None | odds 2.66 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
4. FC St. Pauli vs FSV Mainz 05 | start  | sport None | h2h | FC St. Pauli | None | odds 2.94 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
5. Manchester United vs Liverpool | start  | sport None | h2h | Liverpool | None | odds 3.1 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
6. Humberto Bandenay vs Sang Won Kim | start  | sport None | h2h | Sang Won Kim | None | odds 2.65 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low bookmaker count (6 books) and MMA sport make it less suitable for 'strong singles' even for watchlist consideration, despite its pre_score.
7. Liverpool vs Chelsea | start  | sport None | h2h | Chelsea | None | odds 3.85 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
8. Boston Celtics vs Philadelphia 76ers | start  | sport None | h2h | Philadelphia 76ers | None | odds 3.58 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
9. Fulham vs Bournemouth | start  | sport None | h2h | Fulham | None | odds 2.65 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
10. Brett Bye vs Taylor Michels | start  | sport None | h2h | Taylor Michels | None | odds 2.7 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low bookmaker count (6 books) and MMA sport make it less suitable for 'strong singles' even for watchlist consideration, despite its pre_score.
11. Aston Villa vs Tottenham Hotspur | start  | sport None | h2h | Aston Villa | None | odds 2.3 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
12. St. Louis Cardinals vs Los Angeles Dodgers | start  | sport None | h2h | Los Angeles Dodgers | None | odds 1.77 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but lower odds combined with a moderate pre_score/edge mean better value is available elsewhere.
13. Minnesota Twins vs Toronto Blue Jays | start  | sport None | h2h | Minnesota Twins | None | odds 2.22 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
14. Colorado Rockies vs Atlanta Braves | start  | sport None | h2h | Colorado Rockies | None | odds 3.05 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
15. Tampa Bay Rays vs San Francisco Giants | start  | sport None | h2h | San Francisco Giants | None | odds 1.99 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
16. Washington Nationals vs Milwaukee Brewers | start  | sport None | h2h | Milwaukee Brewers | None | odds 1.83 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but lower odds combined with a moderate pre_score/edge mean better value is available elsewhere.
17. Boston Red Sox vs Houston Astros | start  | sport None | h2h | Houston Astros | None | odds 2.12 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
18. Sunderland vs Manchester United | start  | sport None | h2h | Manchester United | None | odds 1.95 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but the pre_score and edge are not as compelling as selected watchlist items.
19. Seattle Mariners vs Kansas City Royals | start  | sport None | h2h | Seattle Mariners | None | odds 1.76 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but lower odds combined with a moderate pre_score/edge mean better value is available elsewhere.
20. Pittsburgh Pirates vs Cincinnati Reds | start  | sport None | h2h | Pittsburgh Pirates | None | odds 1.81 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good books, but lower odds combined with a moderate pre_score/edge mean better value is available elsewhere.

