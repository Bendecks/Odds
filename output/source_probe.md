# DATA SOURCE PROBE

## the_odds_api_sports — ✅ OK
- status_code: 200
- sample: `[{"key": "americanfootball_ncaaf", "group": "American Football", "title": "NCAAF", "description": "US College Football", "active": true, "has_outrights": false}, {"key": "americanfootball_ncaaf_championship_winner", "group": "American Football", "title": "NCAAF Championship Winner", "description": "US College Football Championship Winner", "active": true, "has_outrights": true}]`

## the_odds_api_upcoming_h2h_eu — ✅ OK
- status_code: 200
- sample: `[{"id": "41653e5ff2659f25c8d53f1652244bb6", "sport_key": "soccer_spain_segunda_division", "sport_title": "La Liga 2 - Spain", "commence_time": "2026-04-27T18:30:00Z", "home_team": "Cádiz CF", "away_team": "Las Palmas", "bookmakers": [{"key": "betsson", "title": "Betsson", "last_update": "2026-04-27T20:26:28Z", "markets": [{"key": "h2h", "last_update": "2026-04-27T20:26:28Z", "outcomes": [{"name": "Cádiz CF", "price": 101.0}, {"name": "Las Palmas", "price": 1.0}, {"name": "Draw", "price": 15.0}]}]}, {"key": "winamax_de", "title": "Winamax (DE)", "last_update": "2026-04-27T20:25:40Z", "markets": [{"key": "h2h", "last_update": "2026-04-27T20:25:40Z", "outcomes": [{"name": "Cádiz CF", "price": 1000.0}, {"name": "Las Palmas", "price": 1.01}, {"name": "Draw", "price": 24.0}]}]}, {"key": "nordicbet", "title": "Nordic Bet", "last_update": "2026-04-27T20:26:12Z", "markets": [{"key": "h2h", "last_update": "2026-04-27T20:26:12Z", "outcomes": [{"name": "Cádiz CF", "price": 101.0}, {"name": "Las Palmas", "price": 1.0}, {"name": "Draw", "price": 15.0}]}]}, {"key": "winamax_fr", "title": "Winamax (FR)", "last_update": "2026-04-27T20:25:01Z", "markets": [{"key": "h2h", "last_update": "2026-04-27T2`

## odds_api_io_status — ✅ OK
- status_code: 200
- sample: `[{"name": "Football", "slug": "football"}, {"name": "Basketball", "slug": "basketball"}]`

## football_data — ❌ FEJL/MANGLER
- status_code: None
- error: Missing FOOTBALL_DATA_API_KEY secret

## balldontlie — ❌ FEJL/MANGLER
- status_code: None
- error: Missing BALLDONTLIE_API_KEY secret

