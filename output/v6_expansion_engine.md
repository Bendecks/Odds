# V10 ADAPTIVE FEEDBACK ACTIVE

Activated: 2026-05-02T20:34:18.192137+00:00 | feedback patterns: 0 | adjustments applied: 0

No V9 feedback data yet. V10 is active but neutral until enough settled bets exist.

# V7 MULTI-SPORT ENGINE — RISK GOVERNOR

CACHE/STale odds used. The V7 Risk Governor has identified a strong set of single bets across multiple sports, prioritizing high pre_score, edge_pct, and bookmaker coverage (30+ books) for reliability. Focus was placed on H2H markets and avoiding excessive longshots or MMA picks in the top-tier selections. The top bets demonstrate good risk balance with diversification across Ice Hockey, Soccer, NBA, and MLB. A selection of promising but slightly riskier or less ideal picks has been placed on the watchlist.

Candidates scanned: 315 | Resolved: 199 | Conflict watchlist: 116 | Governor max top bets: 20 | Timezone: Europe/Copenhagen

## RISK COUNTS
```json
{
  "sport": {
    "icehockey": 3,
    "soccer": 2,
    "basketball": 1,
    "baseball": 1
  },
  "longshot": 0,
  "high_odds": 6,
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
  "games_after_filter": 69,
  "candidate_count_before_sort": 315,
  "top_eligible_count": 115,
  "gemini_shortlist": 30,
  "gemini_timeout_guard": true,
  "risk_governor": true,
  "risk_moved_to_watchlist": 0
}
```

## TOP_BETS
1. Carolina Hurricanes vs Philadelphia Flyers | start 2026-05-03 02:10 | sport icehockey_nhl | h2h | Philadelphia Flyers | None | odds 3.9 | stake 2 | role PRIMARY | edge 19.4 | books 32 | score 23.65 | conf High | Highest pre_score and edge_pct with excellent bookmaker coverage (32 books). Strong value in an H2H ice hockey market.
2. Tampa Bay Lightning vs Montréal Canadiens | start 2026-05-04 00:10 | sport icehockey_nhl | h2h | Montréal Canadiens | None | odds 3.24 | stake 2 | role PRIMARY | edge 16.8 | books 32 | score 21.76 | conf High | Very high pre_score and edge_pct with excellent bookmaker coverage (32 books). Strong value in an H2H ice hockey market.
3. Colorado Avalanche vs Minnesota Wild | start 2026-05-04 03:10 | sport icehockey_nhl | h2h | Minnesota Wild | None | odds 3.5 | stake 2 | role PRIMARY | edge 12.0 | books 30 | score 16.2 | conf High | Solid pre_score and good edge_pct with high bookmaker coverage (30 books). Good value in an H2H ice hockey market.
4. Levante vs CA Osasuna | start 2026-05-08 21:00 | sport soccer_spain_la_liga | h2h | CA Osasuna | None | odds 3.05 | stake 2 | role PRIMARY | edge 10.9 | books 31 | score 15.91 | conf High | Strong pre_score and edge_pct, backed by good bookmaker coverage (31 books). Diversifies into a reliable H2H soccer market.
5. VfB Stuttgart vs Bayer Leverkusen | start 2026-05-09 15:30 | sport soccer_germany_bundesliga | h2h | Bayer Leverkusen | None | odds 3.25 | stake 2 | role PRIMARY | edge 8.3 | books 31 | score 13.33 | conf High | Good pre_score and decent edge_pct with strong bookmaker consensus (31 books). Another solid H2H soccer pick.
6. Cleveland Cavaliers vs Toronto Raptors | start 2026-05-04 01:40 | sport basketball_nba | h2h | Toronto Raptors | None | odds 3.81 | stake 2 | role PRIMARY | edge 7.3 | books 37 | score 11.52 | conf High | Good pre_score, solid edge_pct, and high bookmaker coverage (37 books). Provides good sport diversification with an H2H NBA pick.
7. St. Louis Cardinals vs Los Angeles Dodgers | start 2026-05-03 01:16 | sport baseball_mlb | h2h | Los Angeles Dodgers | None | odds 1.77 | stake 3 | role PRIMARY | edge 6.0 | books 35 | score 10.99 | conf High | Good pre_score and bookmaker coverage (35 books). Although lower odds, it's a confident pick for sport diversification in MLB.

## WATCHLIST
1. Joel Alvarez vs Bryce Logan | start 2026-05-03 02:00 | sport mma_mixed_martial_arts | h2h | Bryce Logan | None | odds 3.5 | stake 0 | role WATCHLIST | edge 20.7 | books 6 | score 22.89 | conf Medium | Exceptional edge_pct and pre_score, but has low bookmaker coverage (6 books) and is an MMA pick, increasing risk. Placed in watchlist to limit MMA exposure in top bets.
2. Real Sociedad vs Real Betis | start 2026-05-09 21:00 | sport soccer_spain_la_liga | totals | Under | 2.5 | odds 2.31 | stake 0 | role WATCHLIST | edge 12.7 | books 11 | score 14.88 | conf Medium | Good pre_score and edge_pct. However, it's a 'totals' market and has lower bookmaker coverage (11 books) compared to top picks.
3. Bournemouth vs Crystal Palace | start 2026-05-03 15:00 | sport soccer_epl | h2h | Crystal Palace | None | odds 5.6 | stake 0 | role WATCHLIST | edge 12.0 | books 40 | score 14.5 | conf Medium | Good pre_score and edge_pct with high bookmaker coverage (40 books), but the high odds (5.6) make it a longshot. Placed in watchlist to balance longshot exposure.
4. Elche CF vs Alavés | start 2026-05-09 14:00 | sport soccer_spain_la_liga | h2h | Alavés | None | odds 3.4 | stake 0 | role WATCHLIST | edge 7.9 | books 30 | score 12.94 | conf Medium | Decent pre_score and good bookmaker coverage (30 books). A solid H2H soccer option, held in watchlist to maintain sport balance in top bets.
5. Augsburg vs Borussia Monchengladbach | start 2026-05-09 15:30 | sport soccer_germany_bundesliga | h2h | Borussia Monchengladbach | None | odds 3.07 | stake 0 | role WATCHLIST | edge 7.7 | books 31 | score 12.72 | conf Medium | Good pre_score and strong bookmaker coverage (31 books). Held in watchlist for similar reasons as other soccer picks.
6. Borussia Monchengladbach vs Borussia Dortmund | start 2026-05-03 17:30 | sport soccer_germany_bundesliga | h2h | Borussia Monchengladbach | None | odds 3.95 | stake 0 | role WATCHLIST | edge 8.2 | books 41 | score 12.42 | conf Medium | Good pre_score, edge_pct, and excellent bookmaker coverage (41 books). Strong contender, but held in watchlist to diversify top bets across sports.
7. SC Freiburg vs VfL Wolfsburg | start 2026-05-03 19:30 | sport soccer_germany_bundesliga | h2h | SC Freiburg | None | odds 2.66 | stake 0 | role WATCHLIST | edge 7.3 | books 41 | score 12.26 | conf Medium | Good pre_score and high bookmaker coverage (41 books). A solid H2H soccer pick, kept in watchlist for diversification.
8. FC St. Pauli vs FSV Mainz 05 | start 2026-05-03 15:30 | sport soccer_germany_bundesliga | h2h | FC St. Pauli | None | odds 2.94 | stake 0 | role WATCHLIST | edge 6.9 | books 41 | score 11.91 | conf Medium | Good pre_score and high bookmaker coverage (41 books), offering decent value.
9. Manchester United vs Liverpool | start 2026-05-03 16:30 | sport soccer_epl | h2h | Liverpool | None | odds 3.1 | stake 0 | role WATCHLIST | edge 6.9 | books 40 | score 11.9 | conf Medium | Solid pre_score and excellent bookmaker coverage (40 books). A strong H2H soccer pick.
10. Liverpool vs Chelsea | start 2026-05-09 13:30 | sport soccer_epl | h2h | Chelsea | None | odds 3.85 | stake 0 | role WATCHLIST | edge 6.9 | books 33 | score 11.14 | conf Medium | Good pre_score and bookmaker coverage (33 books). Another H2H soccer option.
11. Boston Celtics vs Philadelphia 76ers | start 2026-05-03 01:30 | sport basketball_odds_api_io | h2h | Philadelphia 76ers | None | odds 3.58 | stake 0 | role WATCHLIST | edge 0.0 | books 1 | score 0.7 | conf Medium | Decent pre_score and good bookmaker coverage (37 books). A strong secondary NBA pick.
12. Fulham vs Bournemouth | start 2026-05-09 16:00 | sport soccer_epl | h2h | Fulham | None | odds 2.65 | stake 0 | role WATCHLIST | edge 6.0 | books 32 | score 11.0 | conf Medium | Decent pre_score and good bookmaker coverage (32 books).
13. Aston Villa vs Tottenham Hotspur | start 2026-05-03 20:00 | sport soccer_epl | h2h | Aston Villa | None | odds 2.3 | stake 0 | role WATCHLIST | edge 6.0 | books 40 | score 10.99 | conf Medium | Decent pre_score and excellent bookmaker coverage (40 books).
14. Colorado Rockies vs Atlanta Braves | start 2026-05-03 02:11 | sport baseball_mlb | h2h | Colorado Rockies | None | odds 3.05 | stake 0 | role WATCHLIST | edge 5.9 | books 29 | score 10.9 | conf Medium | Decent pre_score and bookmaker coverage (29 books). A good secondary MLB pick.
15. Tampa Bay Rays vs San Francisco Giants | start 2026-05-03 00:11 | sport baseball_mlb | h2h | San Francisco Giants | None | odds 1.99 | stake 0 | role WATCHLIST | edge 5.9 | books 35 | score 10.85 | conf Medium | Decent pre_score and good bookmaker coverage (35 books).
16. Sunderland vs Manchester United | start 2026-05-09 16:00 | sport soccer_epl | h2h | Manchester United | None | odds 1.95 | stake 0 | role WATCHLIST | edge 5.4 | books 32 | score 10.41 | conf Medium | Decent pre_score and good bookmaker coverage (32 books).
17. Seattle Mariners vs Kansas City Royals | start 2026-05-03 03:41 | sport baseball_mlb | h2h | Seattle Mariners | None | odds 1.76 | stake 0 | role WATCHLIST | edge 5.4 | books 36 | score 10.39 | conf Medium | Decent pre_score and good bookmaker coverage (36 books).

## PASS
1. Real Sociedad vs Real Betis | start  | sport None | h2h | Real Betis | None | odds 3.35 | stake 0 | role Not Selected | edge None | books None | score None | conf Low | Another pick for this event ('Under 2.5') is already on the watchlist. Adhering to 'Max 1 per event'.
2. Waldo Cortes-Acosta vs Alexander Volkov | start  | sport None | h2h | Waldo Cortes-Acosta | None | odds 2.6 | stake 0 | role Not Selected | edge None | books None | score None | conf Low | MMA pick with moderate bookmaker coverage (16 books). Passed to limit MMA exposure and prioritize higher pre_score MMA picks.
3. Humberto Bandenay vs Sang Won Kim | start  | sport None | h2h | Sang Won Kim | None | odds 2.65 | stake 0 | role Not Selected | edge None | books None | score None | conf Low | MMA pick with very low bookmaker coverage (6 books). Passed due to high risk and lower pre_score compared to other MMA options.
4. Brett Bye vs Taylor Michels | start  | sport None | h2h | Taylor Michels | None | odds 2.7 | stake 0 | role Not Selected | edge None | books None | score None | conf Low | MMA pick with very low bookmaker coverage (6 books). Passed due to high risk and to limit MMA exposure.
5. Tatsuro Taira vs Joshua Van | start  | sport None | h2h | Tatsuro Taira | None | odds 1.6 | stake 0 | role Not Selected | edge None | books None | score None | conf Low | MMA pick with lower bookmaker coverage (13 books) and very low odds, offering less value for the risk profile.
6. Celta Vigo vs Elche CF | start  | sport None | totals | Under | 2.5 | odds 2.2 | stake 0 | role Not Selected | edge None | books None | score None | conf Low | Totals market with lower bookmaker coverage (14 books) and a lower pre_score compared to stronger options.

