# Automatic closing-price capture

The new-model validation path records Bet365 prices close to kickoff so CLV can be measured without manual input.

## Safety contract

- Only `PAPER PICK` / `PLAY` signals enter the queue.
- A capture is eligible only when the original pick contains an exact Odds-API.io Bet365 event id and `event_match_method=exact`.
- The capture worker never fuzzy-matches an event and never creates a betting decision.
- It reads only Bet365 H2H/ML/1X2 prices for the original pick.
- It is capped at 10 Odds-API.io odds calls per hourly run and makes zero provider calls when no exact signal is due.
- Raw provider responses are not committed. Only compact closing-price records and status are retained.
- Closing prices feed CLV/validation only; they cannot promote the engine to LIVE by themselves.

## Timing

The worker runs hourly. The queue uses a 75-minute pre-kickoff window in the scheduled workflow so an hourly run has overlap and is unlikely to miss a signal. Captured signal keys are skipped on later runs.

## Identity

The Bet365 event id is attached at the exact cross-provider join, propagated through the decision and signal ledger, and then reused by the closing-price worker. Older signals without this identity remain uncaptured rather than being guessed.
