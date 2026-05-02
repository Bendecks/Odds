# V10 ADAPTIVE FEEDBACK ACTIVE

Activated: 2026-05-02T16:38:43.570555+00:00 | feedback patterns: 0 | adjustments applied: 0

No V9 feedback data yet. V10 is active but neutral until enough settled bets exist.

# V7 MULTI-SPORT ENGINE — RISK GOVERNOR

CACHE/STale odds used. Selected a concentrated portfolio of strong single bets, prioritizing high pre_score and edge_pct from a good number of bookmakers. Adhered to risk balance by avoiding picks with low bookmaker counts (especially all MMA selections) and carefully managing exposure to longshots. The top bets represent the highest confidence opportunities across different sports, with additional strong value plays placed on the watchlist.

Candidates scanned: 374 | Resolved: 244 | Conflict watchlist: 130 | Governor max top bets: 20 | Timezone: Europe/Copenhagen

## RISK COUNTS
```json
{
  "sport": {
    "icehockey": 3,
    "soccer": 1
  },
  "longshot": 0,
  "high_odds": 4,
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
  "games_after_filter": 68,
  "candidate_count_before_sort": 374,
  "top_eligible_count": 126,
  "gemini_shortlist": 30,
  "gemini_timeout_guard": true,
  "risk_governor": true,
  "risk_moved_to_watchlist": 0
}
```

## TOP_BETS
1. Carolina Hurricanes vs Philadelphia Flyers | start 2026-05-03 02:10 | sport icehockey_nhl | h2h | Philadelphia Flyers | None | odds 3.9 | stake 2 | role PRIMARY | edge 19.4 | books 32 | score 23.65 | conf High | Highest pre_score and excellent edge_pct. Despite slightly higher odds, the underlying value and widespread bookmaker support make this a strong single pick.
2. Tampa Bay Lightning vs Montréal Canadiens | start 2026-05-04 00:10 | sport icehockey_nhl | h2h | Montréal Canadiens | None | odds 3.24 | stake 2 | role PRIMARY | edge 16.8 | books 32 | score 21.76 | conf High | Second highest pre_score with a significant edge_pct. Good odds and high bookmaker count make this a robust value play.
3. Colorado Avalanche vs Minnesota Wild | start 2026-05-04 03:10 | sport icehockey_nhl | h2h | Minnesota Wild | None | odds 3.5 | stake 2 | role PRIMARY | edge 12.0 | books 30 | score 16.2 | conf High | Strong pre_score and edge_pct. The odds are competitive, and with solid bookmaker coverage, this is a confident selection.
4. Levante vs CA Osasuna | start 2026-05-08 21:00 | sport soccer_spain_la_liga | h2h | CA Osasuna | None | odds 3.05 | stake 2 | role PRIMARY | edge 10.9 | books 31 | score 15.91 | conf High | Excellent pre_score and edge_pct for a soccer pick. The odds are attractive and the pick is well-supported by numerous bookmakers, diversifying the portfolio.

## WATCHLIST
1. Bournemouth vs Crystal Palace | start 2026-05-03 15:00 | sport soccer_epl | h2h | Crystal Palace | None | odds 5.6 | stake 0 | role WATCHLIST | edge 12.0 | books 40 | score 14.5 | conf Medium | Very strong edge_pct and good pre_score. The high odds make it a significant longshot, hence on the watchlist rather than a top bet for risk balance, but worth monitoring.
2. VfB Stuttgart vs Bayer Leverkusen | start 2026-05-09 15:30 | sport soccer_germany_bundesliga | h2h | Bayer Leverkusen | None | odds 3.25 | stake 0 | role WATCHLIST | edge 8.3 | books 31 | score 13.33 | conf Medium | Solid pre_score and decent edge_pct. Offers good value and a moderate risk profile, making it a strong candidate for potential inclusion.
3. New York Yankees vs Baltimore Orioles | start 2026-05-02 19:36 | sport baseball_mlb | h2h | Baltimore Orioles | None | odds 2.5 | stake 0 | role WATCHLIST | edge 6.4 | books 36 | score 11.38 | conf Medium | Good pre_score and edge_pct for a baseball pick. Lower odds but still strong value, providing sport diversity for potential bets.
4. Boston Celtics vs Philadelphia 76ers | start 2026-05-03 01:30 | sport basketball_odds_api_io | h2h | Philadelphia 76ers | None | odds 3.58 | stake 0 | role WATCHLIST | edge 0.0 | books 1 | score 0.7 | conf Medium | Decent pre_score and edge_pct for an NBA pick. Odds are borderline longshot, offering good potential return for the perceived value.

## PASS
1. Joel Alvarez vs Bryce Logan | start  | sport None | h2h | Bryce Logan | None | odds 3.5 | stake 0 | role Pass | edge None | books None | score None | conf Low | Despite high edge_pct and pre_score, the extremely low bookmaker count (6 books) makes this a 'low-bookmaker pick' and thus too risky for strong singles.
2. Humberto Bandenay vs Sang Won Kim | start  | sport None | h2h | Sang Won Kim | None | odds 2.65 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low bookmaker count (6 books) renders this pick too unreliable and risky, despite the decent metrics.
3. Brett Bye vs Taylor Michels | start  | sport None | h2h | Taylor Michels | None | odds 2.7 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low bookmaker count (6 books) makes this pick too volatile and unsuitable for strong singles, despite its statistical appeal.
4. Elche CF vs Alavés | start  | sport None | h2h | Alavés | None | odds 3.4 | stake 0 | role Pass | edge None | books None | score None | conf Low | While decent, other picks offered stronger value or better risk diversification for the watchlist.
5. Augsburg vs Borussia Monchengladbach | start  | sport None | h2h | Borussia Monchengladbach | None | odds 3.07 | stake 0 | role Pass | edge None | books None | score None | conf Low | Reasonable value, but other watchlist candidates offered more compelling attributes or diversity.
6. Borussia Monchengladbach vs Borussia Dortmund | start  | sport None | h2h | Borussia Monchengladbach | None | odds 3.95 | stake 0 | role Pass | edge None | books None | score None | conf Low | Longshot odds combined with slightly lower pre_score/edge compared to top picks meant it didn't make the cut for either top bets or watchlist.
7. SC Freiburg vs VfL Wolfsburg | start  | sport None | h2h | SC Freiburg | None | odds 2.66 | stake 0 | role Pass | edge None | books None | score None | conf Low | Slightly lower pre_score and edge_pct compared to selected picks, making it less compelling for a concentrated portfolio.
8. FC St. Pauli vs FSV Mainz 05 | start  | sport None | h2h | FC St. Pauli | None | odds 2.94 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics compared to the chosen top bets and watchlist entries.
9. Manchester United vs Liverpool | start  | sport None | h2h | Liverpool | None | odds 3.1 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics compared to the chosen top bets and watchlist entries.
10. Cleveland Cavaliers vs Toronto Raptors | start  | sport None | h2h | Toronto Raptors | None | odds 3.81 | stake 0 | role Pass | edge None | books None | score None | conf Low | Borderline longshot with slightly lower metrics than higher-priority basketball picks for the watchlist.
11. Liverpool vs Chelsea | start  | sport None | h2h | Chelsea | None | odds 3.85 | stake 0 | role Pass | edge None | books None | score None | conf Low | Longshot odds combined with slightly lower pre_score/edge compared to stronger soccer picks.
12. Athletics vs Cleveland Guardians | start  | sport None | h2h | Cleveland Guardians | None | odds 2.25 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower pre_score and edge_pct compared to the selected baseball pick for the watchlist.
13. Fulham vs Bournemouth | start  | sport None | h2h | Fulham | None | odds 2.65 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics and insufficient edge compared to stronger soccer picks.
14. Aston Villa vs Tottenham Hotspur | start  | sport None | h2h | Aston Villa | None | odds 2.3 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics and insufficient edge compared to stronger soccer picks.
15. St. Louis Cardinals vs Los Angeles Dodgers | start  | sport None | h2h | Los Angeles Dodgers | None | odds 1.77 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low odds, despite a decent pre_score, indicate less value relative to other options.
16. Minnesota Twins vs Toronto Blue Jays | start  | sport None | h2h | Minnesota Twins | None | odds 2.22 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics compared to the selected baseball pick for the watchlist.
17. Colorado Rockies vs Atlanta Braves | start  | sport None | h2h | Colorado Rockies | None | odds 3.05 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower pre_score and edge_pct, and fewer books, making it less compelling than other options.
18. Tampa Bay Rays vs San Francisco Giants | start  | sport None | h2h | San Francisco Giants | None | odds 1.99 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics and insufficient edge compared to stronger baseball picks.
19. Washington Nationals vs Milwaukee Brewers | start  | sport None | h2h | Milwaukee Brewers | None | odds 1.83 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower odds and insufficient edge compared to stronger baseball picks.
20. Boston Red Sox vs Houston Astros | start  | sport None | h2h | Houston Astros | None | odds 2.12 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower metrics and insufficient edge compared to stronger baseball picks.
21. Sunderland vs Manchester United | start  | sport None | h2h | Manchester United | None | odds 1.95 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low odds and lower edge_pct, indicating less value compared to other soccer selections.
22. Seattle Mariners vs Kansas City Royals | start  | sport None | h2h | Seattle Mariners | None | odds 1.76 | stake 0 | role Pass | edge None | books None | score None | conf Low | Low odds and lower edge_pct, indicating less value compared to other baseball selections.

