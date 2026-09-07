# Public football data probe

Generated: 2026-09-07T09:01:19Z
Mode: SHADOW_ONLY
Production impact: none
Provider: public football results data
Football-Data season: 2627
Openfootball season: 2026-27
Source status: ok
Leagues data-ready: 7 / 14

This probe validates public match-result CSV availability for future SHADOW_ONLY model work.
It does not affect PAPER PICK qualification and does not count as calibrated model evidence.

## Required before model-role promotion
- stable public results coverage for target leagues
- candidate league names mapped to public data league codes
- historical-results adapter implemented
- Dixon-Coles/Elo probabilities calibrated out-of-sample
- model role shadow-tested inside Reference Quality Gate

## Source summary

### football-data.co.uk
- status: source_unavailable
- data_ready: 0 / 7
- rows: 0
- completed_result_rows: 0

### openfootball/football.json
- status: ok
- data_ready: 7 / 7
- rows: 2610
- completed_result_rows: 166

## League probes

### Premier League (football-data.co.uk, E0)
- ok: False
- status_code: None
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/E0.csv
- error: <urlopen error timed out>
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Championship (football-data.co.uk, E1)
- ok: False
- status_code: None
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/E1.csv
- error: <urlopen error timed out>
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Bundesliga (football-data.co.uk, D1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/D1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### La Liga (football-data.co.uk, SP1)
- ok: False
- status_code: None
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/SP1.csv
- error: <urlopen error timed out>
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Serie A (football-data.co.uk, I1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/I1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Ligue 1 (football-data.co.uk, F1)
- ok: False
- status_code: None
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/F1.csv
- error: <urlopen error timed out>
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Eredivisie (football-data.co.uk, N1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/N1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Premier League (openfootball/football.json, E0)
- ok: True
- status_code: 200
- row_count: 380
- completed_result_rows: 20
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.1.json

### Championship (openfootball/football.json, E1)
- ok: True
- status_code: 200
- row_count: 552
- completed_result_rows: 36
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.2.json

### Bundesliga (openfootball/football.json, D1)
- ok: True
- status_code: 200
- row_count: 306
- completed_result_rows: 9
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/de.1.json

### La Liga (openfootball/football.json, SP1)
- ok: True
- status_code: 200
- row_count: 380
- completed_result_rows: 30
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/es.1.json

### Serie A (openfootball/football.json, I1)
- ok: True
- status_code: 200
- row_count: 380
- completed_result_rows: 20
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/it.1.json

### Ligue 1 (openfootball/football.json, F1)
- ok: True
- status_code: 200
- row_count: 306
- completed_result_rows: 18
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/fr.1.json

### Eredivisie (openfootball/football.json, N1)
- ok: True
- status_code: 200
- row_count: 306
- completed_result_rows: 33
- url: https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/nl.1.json
