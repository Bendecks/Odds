# Automatic new-model settlement

Mature new-model H2H signals are reconciled against the original Odds-API.io event id and final score.

## Safety contract

- Only signals already recorded as `PAPER PICK` or `PLAY` can enter settlement.
- Only exact Bet365 provider identities are eligible. Missing/legacy identities are skipped rather than guessed.
- The worker currently settles only H2H/ML/1X2 signals.
- Settled/finished/completed events are scored from the provider home/away result; cancelled/void/postponed events are recorded as void.
- Pending/live or malformed results remain unresolved.
- The worker is capped at 20 event calls every six hours.
- If a captured Bet365 closing price exists for the signal, it is attached to the settlement for CLV analysis.
- Settlement data affects validation statistics only. It does not automatically switch the policy from PAPER to LIVE.

The event endpoint is queried by the provider event id retained at the original exact Bet365 join, avoiding a second cross-provider name match after the match has started.
