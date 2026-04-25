---
date: 2026-04-24
topic: spike-game-read
---

# Spike Game Read Endpoint

## Problem Frame

The current game read endpoint (`GET /players/{player_id}/games/{game_id}`) returns fundamentally different response shapes for in-progress and completed games. `StartedGame` includes round-specific state (bids, tricks, hands) for only the active round. `CompletedGame` drops all round detail entirely -- just a winner, cumulative scores, and a flat player list.

A UI being built against this API needs the full history of a game: every round's bids, hands, discards, tricks, and scores. It also needs a consistent response shape regardless of game completion state. The current split forces the client to handle two unrelated models and provides no access to historical round data.

The action-walking replay infrastructure (`Game.events` from the event-derivation refactor) already reconstructs full game history including dealt hands. The data is available; the read endpoint just doesn't expose it in a usable shape.

A UI mockup (`mockup.svg` at repo root) illustrates the target: a scoreboard with per-round score columns, historical round sections with full bid history and de-anonymized hands/discards, and an active round with interactive state.

---

## Requirements

**Unified response model**

- R1. The spike endpoint returns the same response shape for in-progress and completed games. A completed game differs only in having a non-null winner.
- R2. Top-level fields: game identifier, game name, game status (the active round's phase for in-progress games, or "won" for completed games), winner (null when in-progress), ordered player list, cumulative scores, and an ordered list of rounds.

**Structured rounds**

- R3. Each round is a structured object with named fields: dealer, winning bidder and bid amount, trump suit, ordered bid history (all individual bids in sequence), per-player dealt hands, per-player discards, tricks (each with ordered plays and a winning play), and round scores (points earned that round).
- R4. Fields that are not yet determined in an in-progress round are absent or null. For example, trump is null during bidding; tricks are empty before the trick phase; round scores are absent for an incomplete round.

**Visibility rules**

- R5. Completed rounds are fully de-anonymized: all players' dealt hands, all discards (specific cards), and all trick plays are visible to every requesting player.
- R6. The active round follows current visibility rules: the requesting player sees their own dealt hand and discards as specific cards; other players' hands and discards are represented as card counts.
- R7. The active round includes the requesting player's queued actions, the active player identifier, and the round phase.

The following table summarizes how per-player fields vary by round state and viewer:

| Field | Completed round | Active round (self) | Active round (other) |
|---|---|---|---|
| Dealt hand | Full cards | Full cards | Card count |
| Discards | Full cards | Full cards | Card count |
| Queued actions | N/A | Included | N/A |

**Spike deployment**

- R8. The spike endpoint is a new route deployed alongside the existing game read endpoint.
- R9. The existing game read endpoint, events endpoint, and all other game endpoints remain unchanged.

---

## Acceptance Examples

- AE1. **Covers R1, R3, R5.** Given a completed 3-round game, when any player requests the spike endpoint, the response contains 3 rounds each with full dealt hands for all 4 players, all discards as specific cards, complete trick histories with plays and winners, bid histories, and a non-null winner at top level.
- AE2. **Covers R1, R3, R6, R7.** Given an in-progress game in its second round (discarding phase), when the requesting player calls the spike endpoint, the first round is fully de-anonymized. The second (active) round shows the requesting player's hand as specific cards, other players' hands as counts, the requesting player's discards as specific cards, other players' completed discards as counts, the phase as "discarding", and includes the requesting player's queued actions.
- AE3. **Covers R4.** Given a game in the bidding phase of its first round, the round's trump is null, tricks are empty, discards are empty, and round scores are absent.

---

## Success Criteria

- A client can render the full game view -- scoreboard with per-round scores, historical round detail, and active round interactive state -- from a single read to the spike endpoint, without calling the events endpoint.
- The existing game read endpoint and events endpoint continue to work unchanged for current consumers.
- The spike endpoint returns correct de-anonymized data for completed rounds and correctly anonymized data for the active round, matching the visibility table above.

---

## Scope Boundaries

- Replacing the existing game read endpoint (the spike runs alongside it)
- Replacing the events endpoint (explicitly deferred; seen as a future direction)
- Modifying the `hundredandten-engine` package
- Changing the DB persistence format
- Adding write/action functionality to the spike endpoint (it is read-only)

---

## Key Decisions

- **Structured rounds over event grouping**: Each round is a pre-structured object with named fields (dealer, bids, hands, discards, tricks, scores) rather than a flat list of events grouped by round. The server organizes; the client renders directly.
- **Completed rounds are fully de-anonymized**: Once a round is complete, all hands, discards, and plays are open information for every player. This matches physical card game behavior and enables the historical review UI.
- **Active round carries full interactive state**: The requesting player's hand, queued actions, active player, and phase are part of the active round's data. The client renders the entire game view from a single read.
- **Spike approach**: A new endpoint alongside the existing one, not a modification or replacement. Allows iterating on the new shape without breaking existing consumers.

---

## Dependencies / Assumptions

- The action-walking replay in `Game.events` already reconstructs full game history including dealt hands, all bids, discards, tricks, and per-round scores. The spike serializer will build on this infrastructure.
- Per-round scores from the event replay are assumed to represent round-level deltas (not cumulative totals). Planning should verify this against the actual `RoundEnd.scores` values produced by the engine.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R2][Technical] What URL path should the spike endpoint use? (e.g., `/players/{player_id}/games/{game_id}/detail`, a versioned path, or a query parameter on the existing route)
- [Affects R3][Technical] Should the serializer build structured rounds by transforming `Game.events` output, or by adding new properties to the internal `Game` model?
- [Affects R3][Needs research] Verify whether `RoundEnd.scores` contains round-level score deltas or cumulative scores.

---

## Next Steps

-> `/ce-plan` for structured implementation planning
