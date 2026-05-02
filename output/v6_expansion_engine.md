# V10 ADAPTIVE FEEDBACK ACTIVE

Activated: 2026-05-02T16:22:35.961239+00:00 | feedback patterns: 0 | adjustments applied: 0

No V9 feedback data yet. V10 is active but neutral until enough settled bets exist.

# V7 MULTI-SPORT ENGINE — RISK GOVERNOR

CACHE/STale odds used. The V7 Risk Governor strategy focuses on selecting strong single bets with a balanced risk profile. Priority is given to picks with high pre_score values, indicating significant value. We ensure diversity across sports, limit exposure to MMA (max 1 pick), and balance odds to avoid an overconcentration of extreme longshots. Bookmaker coverage is also considered, favoring picks with a high 'books' count where possible. The 'Top Bets' represent the strongest value propositions, while the 'Watchlist' includes solid picks with slightly lower pre_score, higher odds, or those we monitor for potential future upgrades.

Candidates scanned: 376 | Resolved: 245 | Conflict watchlist: 131 | Governor max top bets: 20 | Timezone: Europe/Copenhagen

## RISK COUNTS
```json
{
  "sport": {
    "icehockey": 3,
    "mma": 1,
    "soccer": 4
  },
  "longshot": 0,
  "high_odds": 8,
  "low_books": 1,
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
  "candidate_count_before_sort": 376,
  "top_eligible_count": 130,
  "gemini_shortlist": 30,
  "gemini_timeout_guard": true,
  "risk_governor": true,
  "risk_moved_to_watchlist": 0
}
```

## TOP_BETS
1. Carolina Hurricanes vs Philadelphia Flyers | start 2026-05-03 02:10 | sport icehockey_nhl | h2h | Philadelphia Flyers | None | odds 3.9 | stake 2 | role PRIMARY | edge 19.4 | books 32 | score 23.65 | conf High | Highest pre_score (23.65) and strong edge (19.4%) with excellent bookmaker coverage (32 books) in NHL.
2. Joel Alvarez vs Bryce Logan | start 2026-05-03 02:00 | sport mma_mixed_martial_arts | h2h | Bryce Logan | None | odds 3.5 | stake 1 | role PRIMARY | edge 20.7 | books 6 | score 22.89 | conf High | Exceptional pre_score (22.89) and highest edge (20.7%). Selected as the single strong MMA pick to balance risk, despite lower book count common for the sport.
3. Tampa Bay Lightning vs Montréal Canadiens | start 2026-05-04 00:10 | sport icehockey_nhl | h2h | Montréal Canadiens | None | odds 3.24 | stake 2 | role PRIMARY | edge 16.8 | books 32 | score 21.76 | conf High | Very strong pre_score (21.76) and high edge (16.8%) with extensive bookmaker coverage (32 books) in NHL.
4. Colorado Avalanche vs Minnesota Wild | start 2026-05-04 03:10 | sport icehockey_nhl | h2h | Minnesota Wild | None | odds 3.5 | stake 2 | role PRIMARY | edge 12.0 | books 30 | score 16.2 | conf High | Solid pre_score (16.2) and good edge (12.0%) with reliable bookmaker coverage (30 books) in NHL.
5. Levante vs CA Osasuna | start 2026-05-08 21:00 | sport soccer_spain_la_liga | h2h | CA Osasuna | None | odds 3.05 | stake 2 | role PRIMARY | edge 10.9 | books 31 | score 15.91 | conf High | Strong pre_score (15.91) and decent edge (10.9%) with good bookmaker coverage (31 books) for La Liga soccer.
6. VfB Stuttgart vs Bayer Leverkusen | start 2026-05-09 15:30 | sport soccer_germany_bundesliga | h2h | Bayer Leverkusen | None | odds 3.25 | stake 2 | role PRIMARY | edge 8.3 | books 31 | score 13.33 | conf High | Good pre_score (13.33) and solid edge (8.3%) with strong bookmaker coverage (31 books) for Bundesliga soccer.
7. Elche CF vs Alavés | start 2026-05-09 14:00 | sport soccer_spain_la_liga | h2h | Alavés | None | odds 3.4 | stake 2 | role PRIMARY | edge 7.9 | books 30 | score 12.94 | conf High | Reliable pre_score (12.94) and good edge (7.9%) with sufficient bookmaker coverage (30 books) for La Liga soccer.
8. Augsburg vs Borussia Monchengladbach | start 2026-05-09 15:30 | sport soccer_germany_bundesliga | h2h | Borussia Monchengladbach | None | odds 3.07 | stake 2 | role PRIMARY | edge 7.7 | books 31 | score 12.72 | conf High | Consistent pre_score (12.72) and solid edge (7.7%) with good bookmaker coverage (31 books) for Bundesliga soccer.

## WATCHLIST
1. Bournemouth vs Crystal Palace | start 2026-05-03 15:00 | sport soccer_epl | h2h | Crystal Palace | None | odds 5.6 | stake 0 | role WATCHLIST | edge 12.0 | books 40 | score 14.5 | conf Medium | High pre_score (14.5) and edge (12.0%) but very high odds (5.6) make it a higher-risk longshot, suitable for careful monitoring.
2. Borussia Monchengladbach vs Borussia Dortmund | start 2026-05-03 17:30 | sport soccer_germany_bundesliga | h2h | Borussia Monchengladbach | None | odds 3.95 | stake 0 | role WATCHLIST | edge 8.2 | books 41 | score 12.42 | conf Medium | Good pre_score (12.42) and solid edge (8.2%) on higher odds. A strong contender if top bets are filled.
3. SC Freiburg vs VfL Wolfsburg | start 2026-05-03 19:30 | sport soccer_germany_bundesliga | h2h | SC Freiburg | None | odds 2.66 | stake 0 | role WATCHLIST | edge 7.3 | books 41 | score 12.26 | conf Medium | Solid pre_score (12.26) and edge (7.3%) with favourable odds. A reliable pick for the watchlist.
4. Manchester United vs Liverpool | start 2026-05-03 16:30 | sport soccer_epl | h2h | Liverpool | None | odds 3.1 | stake 0 | role WATCHLIST | edge 6.9 | books 40 | score 11.9 | conf Medium | A marquee EPL matchup with a good pre_score (11.9) and decent edge (6.9%).
5. Cleveland Cavaliers vs Toronto Raptors | start 2026-05-04 01:40 | sport basketball_nba | h2h | Toronto Raptors | None | odds 3.81 | stake 0 | role WATCHLIST | edge 7.3 | books 37 | score 11.52 | conf Medium | Good pre_score (11.52) and edge (7.3%) for an NBA pick, offering good odds.
6. New York Yankees vs Baltimore Orioles | start 2026-05-02 19:36 | sport baseball_mlb | h2h | Baltimore Orioles | None | odds 2.5 | stake 0 | role WATCHLIST | edge 6.4 | books 36 | score 11.38 | conf Medium | Strong pre_score (11.38) and good edge (6.4%) for an MLB game, offering stable odds.
7. Liverpool vs Chelsea | start 2026-05-09 13:30 | sport soccer_epl | h2h | Chelsea | None | odds 3.85 | stake 0 | role WATCHLIST | edge 6.9 | books 33 | score 11.14 | conf Medium | Another solid EPL pick with a good pre_score (11.14) and edge (6.9%), featuring higher but manageable odds.

## PASS
1. Humberto Bandenay vs Sang Won Kim | start  | sport None | h2h | Sang Won Kim | None | odds 2.65 | stake 0 | role Pass | edge None | books None | score None | conf Low | Passed to respect the 'not too many MMA' rule, as one MMA pick was already selected for 'Top Bets'.
2. Brett Bye vs Taylor Michels | start  | sport None | h2h | Taylor Michels | None | odds 2.7 | stake 0 | role Pass | edge None | books None | score None | conf Low | Passed to respect the 'not too many MMA' rule, as one MMA pick was already selected for 'Top Bets'.
3. FC St. Pauli vs FSV Mainz 05 | start  | sport None | h2h | FC St. Pauli | None | odds 2.94 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good pre_score, but other picks offered slightly better value or diversity for 'Top Bets'/'Watchlist'.
4. Bayer Leverkusen vs RB Leipzig | start  | sport None | h2h | RB Leipzig | None | odds 3.1 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good pre_score, but other Bundesliga picks were prioritized for 'Top Bets'/'Watchlist'.
5. Athletics vs Cleveland Guardians | start  | sport None | h2h | Cleveland Guardians | None | odds 2.25 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good pre_score, but other MLB picks or higher-ranked options were preferred for 'Watchlist'.
6. Boston Celtics vs Philadelphia 76ers | start  | sport None | h2h | Philadelphia 76ers | None | odds 3.58 | stake 0 | role Pass | edge None | books None | score None | conf Low | Decent pre_score, but other NBA or higher-ranked options were preferred for 'Watchlist'.
7. Fulham vs Bournemouth | start  | sport None | h2h | Fulham | None | odds 2.65 | stake 0 | role Pass | edge None | books None | score None | conf Low | Decent pre_score, but other EPL or higher-ranked options were preferred for 'Watchlist'.
8. Aston Villa vs Tottenham Hotspur | start  | sport None | h2h | Aston Villa | None | odds 2.3 | stake 0 | role Pass | edge None | books None | score None | conf Low | Decent pre_score, but other EPL or higher-ranked options were preferred for 'Watchlist'.
9. St. Louis Cardinals vs Los Angeles Dodgers | start  | sport None | h2h | Los Angeles Dodgers | None | odds 1.77 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower odds and other MLB picks were prioritized for 'Watchlist' based on overall value.
10. Minnesota Twins vs Toronto Blue Jays | start  | sport None | h2h | Minnesota Twins | None | odds 2.22 | stake 0 | role Pass | edge None | books None | score None | conf Low | Decent pre_score, but other MLB picks or higher-ranked options were preferred for 'Watchlist'.
11. Colorado Rockies vs Atlanta Braves | start  | sport None | h2h | Colorado Rockies | None | odds 3.05 | stake 0 | role Pass | edge None | books None | score None | conf Low | Slightly lower book count (29) compared to others, and other MLB picks were prioritized.
12. Tampa Bay Rays vs San Francisco Giants | start  | sport None | h2h | San Francisco Giants | None | odds 1.99 | stake 0 | role Pass | edge None | books None | score None | conf Low | Decent pre_score, but other MLB picks or higher-ranked options were preferred for 'Watchlist'.
13. Washington Nationals vs Milwaukee Brewers | start  | sport None | h2h | Milwaukee Brewers | None | odds 1.83 | stake 0 | role Pass | edge None | books None | score None | conf Low | Lower odds and other MLB picks were prioritized for 'Watchlist' based on overall value.
14. Alavés vs Athletic Bilbao | start  | sport None | h2h | Alavés | None | odds 2.96 | stake 0 | role Pass | edge None | books None | score None | conf Low | Good pre_score, but other La Liga picks or higher-ranked options were preferred for 'Top Bets'/'Watchlist'.
15. Boston Red Sox vs Houston Astros | start  | sport None | h2h | Houston Astros | None | odds 2.12 | stake 0 | role Pass | edge None | books None | score None | conf Low | Decent pre_score, but other MLB picks or higher-ranked options were preferred for 'Watchlist'.

