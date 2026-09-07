# Public football data probe

Generated: 2026-09-07T07:43:03Z
Mode: SHADOW_ONLY
Production impact: none
Provider: Football-Data.co.uk
Season: 2627
Source status: source_unavailable
Leagues data-ready: 0 / 7

This probe validates public match-result CSV availability for future SHADOW_ONLY model work.
It does not affect PAPER PICK qualification and does not count as calibrated model evidence.

## Required before model-role promotion
- stable public results coverage for target leagues
- candidate league names mapped to public data league codes
- historical-results adapter implemented
- Dixon-Coles/Elo probabilities calibrated out-of-sample
- model role shadow-tested inside Reference Quality Gate

## League probes

### Premier League (E0)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/E0.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Championship (E1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/E1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Bundesliga (D1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/D1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### La Liga (SP1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/SP1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Serie A (I1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/I1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Ligue 1 (F1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/F1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam

### Eredivisie (N1)
- ok: False
- status_code: 503
- row_count: 0
- completed_result_rows: 0
- url: https://www.football-data.co.uk/mmz4281/2627/N1.csv
- error: HTTPError: 503
- missing_required_columns: AwayTeam, Date, FTAG, FTHG, FTR, HomeTeam
