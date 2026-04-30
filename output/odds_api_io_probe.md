# odds-api.io probe

Generated: 2026-04-30T10:34:38.437728+00:00

Tests: 586 | Useful 2xx: 1 | Early stop: True

## Useful responses
1. 200 | apiKey_param | https://api.odds-api.io/v3/sports?apiKey=***
```
[{"name": "Football", "slug": "football"}, {"name": "Basketball", "slug": "basketball"}, {"name": "Tennis", "slug": "tennis"}, {"name": "Baseball", "slug": "baseball"}, {"name": "American Football", "slug": "american-football"}, {"name": "Ice Hockey", "slug": "ice-hockey"}, {"name": "Esports", "slug": "esports"}, {"name": "Darts", "slug": "darts"}, {"name": "MMA", "slug": "mixed-martial-arts"}, {"name": "Boxing", "slug": "boxing"}, {"name": "Handball", "slug": "handball"}, {"name": "Volleyball", "slug": "volleyball"}, {"name": "Snooker", "slug": "snooker"}, {"name": "Table Tennis", "slug": "table-tennis"}, {"name": "Rugby", "slug": "rugby"}, {"name": "Cricket", "slug": "cricket"}, {"name": "Waterpolo", "slug": "water-polo"}, {"name": "Futsal", "slug": "futsal"}, {"name": "Beach Volley", "slug": "beach-volleyball"}, {"name": "Aussie Rules", "slug": "aussie-rules"}, {"name": "Floorball", "
```

## Recent failures/sample
- 404 | apiKey_param | https://api.odds-api.io/v2/odds?apiKey=***&regions=eu%2Cuk | 404 page not found
- 404 | apiKey_param | https://api.odds-api.io/v2/odds?apiKey=***&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | apiKey_param | https://api.odds-api.io/v2/odds?apiKey=***&sport=soccer&regions=eu%2Cuk&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=*** | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&sport=soccer | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&sport=football | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&sport=tennis | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&sport=basketball | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&sports=soccer%2Ctennis%2Cbasketball%2Cicehockey | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&regions=eu%2Cuk | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | api_key_param | https://api.odds-api.io/v2/odds?api_key=***&sport=soccer&regions=eu%2Cuk&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=*** | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&sport=soccer | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&sport=football | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&sport=tennis | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&sport=basketball | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&sports=soccer%2Ctennis%2Cbasketball%2Cicehockey | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&regions=eu%2Cuk | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | key_param | https://api.odds-api.io/v2/odds?key=***&sport=soccer&regions=eu%2Cuk&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?sport=soccer | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?sport=football | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?sport=tennis | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?sport=basketball | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?sports=soccer%2Ctennis%2Cbasketball%2Cicehockey | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?regions=eu%2Cuk | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | x_api_key_header | https://api.odds-api.io/v2/odds?sport=soccer&regions=eu%2Cuk&markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?sport=soccer | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?sport=football | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?sport=tennis | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?sport=basketball | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?sports=soccer%2Ctennis%2Cbasketball%2Cicehockey | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?regions=eu%2Cuk | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?markets=h2h%2Cspreads%2Ctotals | 404 page not found
- 404 | bearer_header | https://api.odds-api.io/v2/odds?sport=soccer&regions=eu%2Cuk&markets=h2h%2Cspreads%2Ctotals | 404 page not found
