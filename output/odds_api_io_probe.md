# odds-api.io probe v4 — low request

Generated: 2026-05-02T06:45:43.827189+00:00

Tests: 5 | Useful 2xx: 3

## Selected league
{
  "name": "Finland - Kolmonen",
  "slug": "finland-kolmonen",
  "eventsCount": 307
}

## Event IDs
- 69921736
- 69923654
- 69924470

## Useful responses
1. 200 | league_list | https://api.odds-api.io/v3/leagues?sport=football&apiKey=***
Params: `{"sport": "football"}`
```
[{"name": "Albania - Kategoria e Pare", "slug": "albania-kategoria-e-pare", "eventsCount": 6}, {"name": "Albania - Kategoria Superiore", "slug": "albania-kategoria-superiore", "eventsCount": 15}, {"name": "Algeria - Ligue 1", "slug": "algeria-ligue-1", "eventsCount": 4}, {"name": "Algeria - Ligue 2", "slug": "algeria-ligue-2", "eventsCount": 24}, {"name": "Andorra - Primera Divisio", "slug": "andorra-primera-divisio", "eventsCount": 9}, {"name": "Andorra - Second Divisio", "slug": "andorra-second-divisio", "eventsCount": 4}, {"name": "Angola - Girabola", "slug": "angola-girabola", "eventsCount": 31}, {"name": "Argentina - Copa Argentina", "slug": "argentina-copa-argentina", "eventsCount": 2}, {"name": "Argentina - Copa Proyeccion Final, Reserves", "slug": "argentina-copa-proyeccion-final-reserves", "eventsCount": 72}, {"name": "Argentina - Liga Profesional", "slug": "argentina-liga-profesional", "eventsCount": 15}, {"name": "Argentina - Primera B", "slug": "argentina-primera-b", "eventsCount": 67}, {"name": "Argentina - Primera C", "slug": "argentina-primera-c", "eventsCount": 82}, {"name": "Argentina - Primera Division, Women", "slug": "argentina-primera-division-women", "eventsCount": 8}, {"name": "Argentina - Primera Nacional", "slug": "argentina-primera-nacional", "eventsCount": 89}, {"name": "Argentina - Torneo Federal A", "slug": "argentina-torneo-federal-a", "eventsCount
```

2. 200 | league_to_events_or_odds | https://api.odds-api.io/v3/events?sport=football&league=finland-kolmonen&apiKey=***
Params: `{"sport": "football", "league": "finland-kolmonen"}`
```
[{"id": 69921736, "home": "MK United", "away": "IF Sibbo Vargarna", "homeId": 1114065, "awayId": 283509, "date": "2026-05-02T11:15:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69923654, "home": "Ylojarvi United FC", "away": "NOPS", "homeId": 1007057, "awayId": 50019, "date": "2026-05-02T11:30:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69924470, "home": "Yllatys", "away": "SC Zulimanit", "homeId": 1131349, "awayId": 2285, "date": "2026-05-02T12:00:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69924642, "home": "Kjp Kouvola", "away": "Ips", "homeId": 889967, "awayId": 283541, "date": "2026-05-02T12:00:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69921092, "home": "Vjs/Akatemia", "away": "Ppj/Lauttasaari", "homeId": 1335286, "awayId": 1124271, "date": "2026-05-02T12:15:00Z", "sport": {"name": "Football", "slug"
```

3. 200 | event_to_odds | https://api.odds-api.io/v3/events/69921736?apiKey=***
Params: `{}`
```
{"id": 69921736, "home": "MK United", "away": "IF Sibbo Vargarna", "homeId": 1114065, "awayId": 283509, "date": "2026-05-02T11:15:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}
```

## All results
- 200 | league_list | https://api.odds-api.io/v3/leagues?sport=football&apiKey=*** | [{"name": "Albania - Kategoria e Pare", "slug": "albania-kategoria-e-pare", "eventsCount": 6}, {"name": "Albania - Kategoria Superiore", "slug": "albania-kategoria-superiore", "eventsCount": 15}, {"name": "Algeria - Ligue 1", "slug": "algeria-ligue-1", "eventsCount": 4}, {"name": "Algeria - Ligue 2", "slug": "algeria-ligue-2", "eventsCount": 24}, {"name": "Andorra - Primera Divisio", "slug": "andorra-primera-divisio", "eventsCount": 9}, {"name": "Andorra - Second Divisio", "slug": "andorra-second-divisio", "eventsCount": 4}, {"name": "Angola - Girabola", "slug": "angola-girabola", "eventsCount": 31}, {"name": "Argentina - Copa Argentina", "slug": "argentina-copa-argentina", "eventsCount": 2}, {"name": "Argentina - Copa Proyeccion Final, Reserves", "slug": "argentina-copa-proyeccion-final-reserves", "eventsCount": 72}, {"name": "Argentina - Liga Profesional", "slug": "argentina-liga-profesional", "eventsCount": 15}, {"name": "Argentina - Primera B", "slug": "argentina-primera-b", "eventsCount": 67}, {"name": "Argentina - Primera C", "slug": "argentina-primera-c", "eventsCount": 82}, {"name": "Argentina - Primera Division, Women", "slug": "argentina-primera-division-women", "eventsCount": 8}, {"name": "Argentina - Primera Nacional", "slug": "argentina-primera-nacional", "eventsCount": 89}, {"name": "Argentina - Torneo Federal A", "slug": "argentina-torneo-federal-a", "eventsCount
- 200 | league_to_events_or_odds | https://api.odds-api.io/v3/events?sport=football&league=finland-kolmonen&apiKey=*** | [{"id": 69921736, "home": "MK United", "away": "IF Sibbo Vargarna", "homeId": 1114065, "awayId": 283509, "date": "2026-05-02T11:15:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69923654, "home": "Ylojarvi United FC", "away": "NOPS", "homeId": 1007057, "awayId": 50019, "date": "2026-05-02T11:30:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69924470, "home": "Yllatys", "away": "SC Zulimanit", "homeId": 1131349, "awayId": 2285, "date": "2026-05-02T12:00:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69924642, "home": "Kjp Kouvola", "away": "Ips", "homeId": 889967, "awayId": 283541, "date": "2026-05-02T12:00:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}, {"id": 69921092, "home": "Vjs/Akatemia", "away": "Ppj/Lauttasaari", "homeId": 1335286, "awayId": 1124271, "date": "2026-05-02T12:15:00Z", "sport": {"name": "Football", "slug"
- 400 | event_to_odds | https://api.odds-api.io/v3/odds?eventId=69921736&apiKey=*** | {"error": "Missing bookmakers"}
- 400 | event_to_odds | https://api.odds-api.io/v3/events?eventId=69921736&apiKey=*** | {"error": "Sport is required"}
- 200 | event_to_odds | https://api.odds-api.io/v3/events/69921736?apiKey=*** | {"id": 69921736, "home": "MK United", "away": "IF Sibbo Vargarna", "homeId": 1114065, "awayId": 283509, "date": "2026-05-02T11:15:00Z", "sport": {"name": "Football", "slug": "football"}, "league": {"name": "Finland - Kolmonen", "slug": "finland-kolmonen"}, "status": "pending", "scores": {"home": 0, "away": 0}}
