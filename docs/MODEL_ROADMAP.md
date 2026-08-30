# Model roadmap

## Current
- Broad Bet365 football discovery: 120 observed market names in the first compact baseline.
- Reference model: H2H/1X2 consensus only.
- Final action: PAPER only, one exact pick/stake or NO BET.

## Next model families
Build reference probability support in this order, while retaining all raw markets throughout:

1. H2H/1X2 including draw — simplest baseline and already supported by the reference provider.
2. Totals — high Bet365 coverage and a standard comparable market.
3. Spread/Asian handicap — high coverage and standard line structure.
4. BTTS / Draw No Bet / Double Chance — derived or closely related match markets after baseline validation.
5. Corners/cards/player props — retain observations now, but defer modelling until there is a defensible independent reference or statistical model.

Order is a modelling priority, not a collection filter. No raw market family is deleted because it is lower priority.

## Promotion evidence
Do not infer profitability from row counts or a short winning segment. Track model version, price timestamp, closing price, result, profit, CLV and calibration. LIVE promotion requires new-model evidence and uncertainty analysis; legacy paper bets do not qualify it.
