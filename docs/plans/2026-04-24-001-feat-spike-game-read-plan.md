---
title: "feat: Add spike game read endpoint with structured round-based response"
type: feat
status: completed
date: 2026-04-24
origin: docs/brainstorms/spike-game-read-requirements.md
---

# feat: Add spike game read endpoint with structured round-based response

## Overview

Add a new read-only game endpoint (`GET /players/{player_id}/games/{game_id}/spike`) that returns a unified, round-based game response. The internal `Game` model gains a `rounds` property that builds structured round objects via action-walking replay (the same technique as `Game.events`, but producing structured rounds instead of flat events). The client serializer maps these internal rounds to one of three discriminated response types: `COMPLETED`, `COMPLETED_NO_BIDDERS`, or an active round with the current phase status. Completed rounds are fully de-anonymized; the active round preserves current visibility rules.

---

## Problem Frame

The current game read endpoint returns fundamentally different response shapes for in-progress and completed games, and only includes the active round's state. A UI being built needs full game history -- scoreboard with per-round scores, historical round detail, and active round interactive state -- from a single read. The action-walking replay technique (`Game.events`) proves structured reconstruction is possible; the spike adds a `Game.rounds` property that produces the right shape directly, making the serializer a straightforward field mapping. (see origin: `docs/brainstorms/spike-game-read-requirements.md`)

---

## Requirements Trace

- R1. Unified response shape for in-progress and completed games (winner is null vs present)
- R2. Top-level fields: id, name, status, winner, players, scores, rounds
- R3. Structured rounds with named fields (dealer, bidder, trump, bid_history, hands, discards, tricks, scores)
- R4. Absent/null fields for in-progress round state not yet determined
- R5. Completed rounds fully de-anonymized
- R6. Active round follows current visibility rules (self sees cards, others see counts)
- R7. Active round includes queued actions, active player, phase
- R8. New route alongside existing endpoint
- R9. Existing endpoints unchanged

**Origin acceptance examples:** AE1 (covers R1, R3, R5), AE2 (covers R1, R3, R6, R7), AE3 (covers R4)

---

## Scope Boundaries

The following are explicitly **out of scope**:

- Modifying the existing game read endpoint, events endpoint, or action/queue endpoints
- Modifying the `hundredandten-engine` package or DB persistence format
- Adding write/action functionality to the spike endpoint
- Removing the events endpoint (superseded by the spike for the full-list use case, but `__events_for_action` is retained for future SignalR integration and current action/queue endpoint responses)

---

## Context & Research

### Relevant Code and Patterns

- `src/models/internal/game.py:204-295` -- `Game.events` property and `__events_for_action` implement action-walking replay. The new `Game.rounds` property uses the same replay technique but produces structured `InternalRound` objects instead of flat events
- `src/models/internal/game.py:410-419` -- `__initialize_engine` constructs the engine and replays all actions. The `rounds` property will use a similar but independent replay with plain `EnginePlayer` instances (same as `events`)
- `src/models/internal/actions.py` -- Internal event/action types as frozen dataclasses. `Card.from_engine()` for converting engine cards
- `src/models/internal/trick.py` -- Existing `Trick` internal model with `bleeding: bool`, `plays: list[Play]`, `winning_play: Optional[Play]`
- `src/mappers/client/serialize.py:39-73` -- Current `game()` serializer branches on `GameStatus.WON` to produce `CompletedGame` or `StartedGame`
- `src/mappers/client/serialize.py:131-152` -- `__player_in_round` helper implements self/other visibility distinction
- `src/models/client/responses.py` -- Pydantic models using `Literal` type discriminators, `Union` types with `Field(discriminator=...)`, and `Optional` fields
- `src/routers/games.py:37-42` -- Existing game read endpoint pattern: `GameService.get()` then `serialize.game()`
- `tests/helpers.py` -- `started_game()`, `completed_game()`, `game_with_manual_player()`, `get_events()`, `get_game()` helpers

### Institutional Learnings

- `docs/solutions/logic-errors/round-start-hands-lost-to-in-place-mutation-2026-04-11.md` -- The engine mutates `RoundPlayer.hand` in-place during discards. The action-walking replay handles this by snapshotting hands immediately after a round appears (before any actions). The `rounds` property must follow the same pattern.
- Use plain `EnginePlayer` (not `Human`/`NaiveCpu`) for replay engines -- keeps the replay passive with no automation side effects.

---

## Key Technical Decisions

- **Round-aware internal model over event-walking serializer**: A new `Game.rounds` property builds structured `InternalRound` objects via action-walking replay. This is cleaner than walking `Game.events` in the serializer because: (a) the serializer becomes trivial field mapping instead of a state machine, (b) `bleeding` is directly available from replay engine trick objects, (c) per-round scores can be computed correctly by summing the engine's `round.scores` entries, and (d) the structured round data serves any future endpoint without re-implementing event walking. `Game.events` and `__events_for_action` remain untouched -- they serve the action/queue endpoints now and SignalR later.
- **Three discriminated client round models**: The API communicates which fields are present for each round type via a discriminated union on the `status` field:
  - `SpikeCompletedRound` (status: `"COMPLETED"`) -- all fields required: dealer, bidder, bid_amount, trump, bid_history, hands, discards, tricks (with `bleeding`), scores
  - `SpikeCompletedNoBiddersRound` (status: `"COMPLETED_NO_BIDDERS"`) -- all-pass round: dealer, bid_history (all passes), hands, scores. No bidder, trump, discards, or tricks
  - `SpikeActiveRound` (status: one of `"BIDDING"`, `"TRUMP_SELECTION"`, `"DISCARD"`, `"TRICKS"`) -- progressive fields depending on phase, plus active_player_id and the requesting player's queued_actions. Hands and discards follow current visibility rules (self sees cards, others see counts)
- **Round-level scores via proper summation of engine `round.scores`**: The existing `RoundEnd.scores` dict comprehension (`game.py:270-274`) is lossy -- it drops duplicate player entries from the engine's per-trick score list. The `rounds` property accesses engine `round.scores` directly and sums duplicate entries correctly. This produces accurate per-round score deltas.
- **Tricks include `bleeding`**: Because the `rounds` property has direct access to the replay engine's trick objects during the walk, it can capture `trick.bleeding` at the natural moment. This is not possible from the flat event stream.
- **Reuse existing `Card`, `PlayerInGame`, `QueuedPlayCard`, `UnorderedActionResponse` models**: These already have the right shape.

---

## Open Questions

### Resolved During Planning

- **Internal model round-awareness is simpler**: Evaluated during planning -- moving round structuring into the internal model eliminates the event-walking serializer, gives access to `bleeding` and correct scores, and creates a reusable domain-level abstraction.
- **`RoundEnd.scores` is lossy**: The dict comprehension drops duplicate player entries. The `rounds` property accesses the engine's `round.scores` list directly and sums correctly.
- **URL path**: `/{game_id}/spike` -- explicitly experimental.
- **`bleeding` available from replay engine**: Unlike the flat event stream, the replay engine's trick objects carry `bleeding` state at the moment tricks complete.

### Deferred to Implementation

- **Bidder derivation for completed rounds**: The winning bidder can be inferred from the bid history (last non-pass bid) or from the `SelectTrump` action's `player_id`. Implementation should pick whichever is cleaner.
- **Exact `InternalRound` field types**: The frozen dataclass field types (especially for hands and discards) should be determined during implementation. Hands are `dict[str, list[Card]]` (always full cards at the internal level). Discards are `dict[str, tuple[Card, ...]]` or `dict[str, list[Card]]` -- follow existing conventions.
- **Score representation for all-pass rounds**: When all players pass, the engine may produce empty scores or all zeros. Implementation should verify and handle consistently.

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
Game.rounds property (new, uses same replay technique as Game.events):

  1. Construct replay engine (EnginePlayer instances, game seed)
  2. Snapshot initial round: dealer, hands
  3. Walk self.actions one at a time:
     - Before/after each action: compare round count and trick count
     - Bid        → append to current round's bid_history
     - SelectTrump → set trump, record bidder
     - Discard    → add to current round's discards
     - Play       → handled by engine (trick state updates)
     - Round boundary detected:
         → Read completed round's tricks (with bleeding) from engine
         → Compute scores by summing engine round.scores entries
         → Close current round as completed
         → Open new round: dealer, hands snapshot
     - Trick boundary detected:
         → Read trick bleeding + winning_play from engine
  4. Last round (no RoundEnd boundary) is the active round
  5. Return list[InternalRound]

Three round patterns:
  Full completed:  dealer, bidder, trump, bids, hands, discards, tricks, scores
  All-pass:        dealer, bids (all passes), hands, scores. No bidder/trump/discards/tricks
  Active:          dealer, partial bids/discards/tricks depending on phase

Client serializer maps InternalRound → discriminated type:
  completed + has bidder    → SpikeCompletedRound      (status: "COMPLETED")
  completed + no bidder     → SpikeCompletedNoBiddersRound (status: "COMPLETED_NO_BIDDERS")
  not completed             → SpikeActiveRound          (status: game phase)

Visibility (applied by serializer, not internal model):
  Completed rounds: all hands/discards as full cards (de-anonymized)
  Active round: self → full cards, others → len() counts
```

---

## Implementation Units

- U1. **Internal round model and `Game.rounds` property**

**Goal:** Add an `InternalRound` frozen dataclass and a `Game.rounds` property that builds structured rounds via action-walking replay.

**Requirements:** R3, R4, R5 (data availability)

**Dependencies:** None

**Files:**
- Create: `src/models/internal/round.py`
- Modify: `src/models/internal/game.py`
- Modify: `src/models/internal/__init__.py` (export new types)
- Test: `tests/mappers/test_game_rounds.py`

**Approach:**
- Define `InternalRound` as a frozen dataclass with fields: `dealer: str`, `bidder: Optional[str]`, `bid_amount: Optional[int]`, `trump: Optional[CardSuit]`, `bid_history: list[Bid]`, `hands: dict[str, list[Card]]`, `discards: dict[str, list[Card]]`, `tricks: list[Trick]` (reuses existing internal `Trick` model -- has `bleeding`), `scores: Optional[dict[str, int]]`, `completed: bool`
- Add `Game.rounds -> list[InternalRound]` property that constructs a replay engine (same technique as `events`) and walks `self.actions`:
  - On construction: snapshot first round's dealer and hands
  - On each action: detect round and trick boundaries by comparing `len(engine.rounds)` and `len(engine.active_round.tricks)` before and after `engine.act()`
  - On trick boundary: read `trick.bleeding`, `trick.plays`, `trick.winning_play` from the replay engine
  - On round boundary: compute per-round scores by summing the engine's `round.scores` entries (not the lossy dict comprehension), read completed round's tricks, close round as completed, open new round with dealer/hands snapshot
  - Final round (no boundary) is the active round with `completed=False`
- `Game.events` and `__events_for_action` remain untouched
- Use plain `EnginePlayer` for the replay (same as `events`)
- Handle all-pass rounds: these produce `completed=True` rounds with no bidder, trump, discards, or tricks. Scores may be empty or all zeros

**Patterns to follow:**
- `Game.events` property at `src/models/internal/game.py:204-231` for the replay setup and action walking
- `Game.__events_for_action` at line 233-295 for round/trick boundary detection
- `src/models/internal/trick.py` for the existing `Trick` model (reused directly)
- Existing frozen dataclass conventions in `src/models/internal/`

**Test scenarios:**
- Happy path: new game (1 round, in progress) -- single round with `completed=False`, correct dealer, 5-card hands for all players
- Happy path: completed game -- all rounds have `completed=True`, correct dealers, hands are pre-discard (5 cards each), tricks have `bleeding` and `winning_play`
- Happy path: bid_history captures all bids in order for each round
- Happy path: discards captured per-player (as full card lists at internal level)
- Happy path: per-round scores sum to `game.scores` cumulative totals
- Edge case: all-pass round -- `completed=True`, no bidder, no trump, empty discards, empty tricks
- Edge case: game-winning round has scores and `completed=True`
- Edge case: active round has partial state depending on current phase (trump null during bidding, discards empty before discard phase, etc.)
- Edge case: tricks carry `bleeding=True` when trump is played on a non-trump lead
- Edge case: hands are pre-mutation snapshots (5 cards), not post-discard

**Verification:**
- `Game.rounds` produces correct rounds for all game states (new, in-progress, completed)
- Sum of all completed rounds' scores equals `game.scores`
- All trick `bleeding` values are correct
- All `hands` contain 5 cards (dealt hands, not post-discard)

---

- U2. **Client round response models**

**Goal:** Define three discriminated Pydantic round models and the `SpikeGame` top-level model.

**Requirements:** R1, R2, R3, R4

**Dependencies:** None (can be implemented in parallel with U1)

**Files:**
- Modify: `src/models/client/responses.py`

**Approach:**
- Add new models in the Games section of responses.py
- `SpikeBid`: `player_id: str`, `amount: int`
- `SpikeTrick`: `bleeding: bool`, `plays: list[QueuedPlayCard]`, `winning_play: Optional[QueuedPlayCard]` -- includes `bleeding` (data is available from the internal model)
- Three round models discriminated by `status`:
  - `SpikeCompletedRound` (status: `Literal["COMPLETED"]`) -- all round fields required: `dealer: str`, `bidder: str`, `bid_amount: int`, `trump: SelectableSuit`, `bid_history: list[SpikeBid]`, `hands: dict[str, list[Card]]`, `discards: dict[str, list[Card]]`, `tricks: list[SpikeTrick]`, `scores: dict[str, int]`
  - `SpikeCompletedNoBiddersRound` (status: `Literal["COMPLETED_NO_BIDDERS"]`) -- all-pass round: `dealer: str`, `bid_history: list[SpikeBid]`, `hands: dict[str, list[Card]]`, `scores: dict[str, int]`
  - `SpikeActiveRound` (status: `Literal["BIDDING", "TRUMP_SELECTION", "DISCARD", "TRICKS"]`) -- progressive optional fields: `dealer: str`, `bid_history: list[SpikeBid]`, `hands: dict[str, Union[list[Card], int]]`, `discards: dict[str, Union[list[Card], int]]`, `bidder: Optional[str]`, `bid_amount: Optional[int]`, `trump: Optional[SelectableSuit]`, `tricks: list[SpikeTrick]`, `active_player_id: str`, `queued_actions: list[UnorderedActionResponse]`
- `SpikeRound` type alias: `Annotated[Union[SpikeCompletedRound, SpikeCompletedNoBiddersRound, SpikeActiveRound], Field(discriminator="status")]`
- `SpikeGame`: `id: str`, `name: str`, `status: str`, `winner: Optional[PlayerInGame]`, `players: list[PlayerInGame]`, `scores: dict[str, int]`, `rounds: list[SpikeRound]`

**Patterns to follow:**
- Existing event discriminated union at `responses.py:115-121` using `Annotated[Union[...], Field(discriminator="type")]`
- `responses.StartedGame` / `responses.CompletedGame` for game-level field conventions
- `responses.RoundStart.hands: dict[str, Union[list[Card], int]]` for visibility polymorphism

**Test scenarios:**
- Test expectation: none -- validated through integration tests in U5

**Verification:**
- All models are importable, Pydantic schema generation succeeds
- Discriminated union serializes/deserializes correctly for all three round types
- `SpikeGame` can be used as a `response_model` in a FastAPI route

---

- U3. **Spike serializer**

**Goal:** Implement the serialization function that maps `Game` (with its `rounds` property) to a `SpikeGame` response, applying visibility rules.

**Requirements:** R1, R2, R3, R4, R5, R6, R7

**Dependencies:** U1, U2

**Files:**
- Modify: `src/mappers/client/serialize.py`
- Test: `tests/mappers/test_spike_serialize.py`

**Approach:**
- Add `spike_game(m_game: internal.Game, client_player_id: str) -> responses.SpikeGame`
- For each `InternalRound` in `m_game.rounds`, map to the appropriate client type:
  - `completed=True` with a bidder → `SpikeCompletedRound` -- all hands/discards as full `list[Card]` (de-anonymized)
  - `completed=True` without a bidder → `SpikeCompletedNoBiddersRound` -- hands as full `list[Card]`
  - `completed=False` → `SpikeActiveRound` -- hands/discards apply visibility: self gets `list[Card]`, others get `int` count. Attach `active_player_id` from `m_game.active_player_id`, queued actions for the requesting player
- Status string for active round: `m_game.status.name` (e.g., `"BIDDING"`, `"TRICKS"`)
- Build top-level `SpikeGame` from `game.id`, `game.name`, `game.status.name`, `game.winner`, `game.ordered_players`, `game.scores`, and mapped rounds
- Reuse existing helpers: `__card()`, `__player_in_game()`, `__play()`, `__player_type()`, `suggestion()` for queued actions

**Patterns to follow:**
- `serialize.game()` at `src/mappers/client/serialize.py:39-73` for the top-level game serialization pattern
- `serialize.__player_in_round()` at line 131-152 for the self/other visibility distinction

**Test scenarios:**
- Happy path: completed round maps to `SpikeCompletedRound` with all hands/discards de-anonymized
- Happy path: all-pass round maps to `SpikeCompletedNoBiddersRound`
- Happy path: active round maps to `SpikeActiveRound` with correct phase status
- Edge case: active round hands -- self sees `list[Card]`, others see `int` count
- Edge case: active round discards -- self sees own discards as `list[Card]`, others' as `int`
- Edge case: completed round hands are identical regardless of requesting player identity
- Edge case: queued actions appear only on active round, only for the requesting player
- Edge case: tricks include `bleeding` for all round types that have tricks

**Verification:**
- Serializer produces correct discriminated types for all round states
- Visibility rules applied only to active round, not completed rounds

---

- U4. **Spike route handler**

**Goal:** Add the `GET /{game_id}/spike` endpoint to the games router.

**Requirements:** R8, R9

**Dependencies:** U2, U3

**Files:**
- Modify: `src/routers/games.py`

**Approach:**
- Add `@router.get("/{game_id}/spike", response_model=responses.SpikeGame)` following the existing `game_info` pattern: `GameService.get()` then `serialize.spike_game()`
- Import `SpikeGame` alongside existing response imports
- Place near the existing `game_info` route

**Patterns to follow:**
- `game_info()` at `src/routers/games.py:37-42`

**Test scenarios:**
- Test expectation: none -- thin delegation; coverage from U5 integration tests

**Verification:**
- Endpoint appears in OpenAPI schema
- Existing game endpoints unchanged

---

- U5. **Integration tests**

**Goal:** End-to-end tests for the spike endpoint covering acceptance examples, visibility rules, and round discrimination.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8, R9

**Dependencies:** U1, U2, U3, U4

**Files:**
- Create: `tests/functions/test_spike_game.py`

**Approach:**
- Add `get_spike_game` helper (analogous to `get_game`)
- Tests use existing helpers (`started_game`, `completed_game`, `game_with_manual_player`) for game state setup
- Assert on discriminated round types via the `status` field in the response
- For de-anonymization: call as two different players, verify identical completed round data
- For visibility: call as two different players, verify different active round hand data

**Patterns to follow:**
- `tests/functions/test_game_events.py` for structure and fixture usage
- `tests/helpers.py` for `started_game()`, `completed_game()`, `game_with_manual_player()`, `queue_action()`

**Test scenarios:**
- Covers AE1. Happy path: completed game -- all rounds present, completed rounds have `status: "COMPLETED"` or `"COMPLETED_NO_BIDDERS"`, de-anonymized hands and discards, tricks with `bleeding`, non-null winner at top level
- Covers AE2. Happy path: in-progress game past first round -- completed rounds are de-anonymized, active round has `status` matching phase, self hand as cards, opponent hands as counts, queued actions present
- Covers AE3. Happy path: new game in bidding phase -- single active round with `status: "BIDDING"`, trump null, tricks empty, discards empty
- Happy path: top-level fields correct -- id, name, status, players (ordered), cumulative scores
- Happy path: `status` reflects `"WON"` for completed games, active phase for in-progress
- Happy path: tricks include `bleeding` field in completed rounds
- Edge case: two different players see identical de-anonymized data for completed rounds
- Edge case: two different players see different hands/discards in the active round
- Edge case: active round includes `active_player_id` matching `game.active_player_id`
- Edge case: all-pass rounds have `status: "COMPLETED_NO_BIDDERS"`, null trump, empty tricks
- Edge case: sum of all completed rounds' `scores` equals top-level `scores`
- Error path: non-existent game ID returns 404

**Verification:**
- All integration tests pass
- `uv run pytest` passes with full coverage
- Existing test files unchanged and passing

---

## System-Wide Impact

- **Interaction graph:** The spike endpoint is read-only. `Game.rounds` uses a replay engine (same technique as `Game.events`) -- no mutation of game state, no DB writes, no side effects. The existing `Game.events`, `__events_for_action`, and all action/queue endpoints are untouched.
- **Error propagation:** Inherits `GameService.get()` error handling (`NotFoundError`). The `rounds` property and serializer are pure transformations.
- **State lifecycle risks:** None. Read-only derivation from persisted state.
- **API surface parity:** Additive. Existing `GET /{game_id}`, `GET /{game_id}/events`, and all action endpoints unchanged.
- **Integration coverage:** The `rounds` property is tested at the internal model level (U1). The serializer is tested at the mapper level (U3). Integration tests (U5) verify the full HTTP path.
- **Unchanged invariants:** `Game.events`, `__events_for_action`, existing endpoints, existing response models, existing serializers all remain untouched. The `/events` endpoint remains available but is considered superseded for the full-list use case.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Engine `round.scores` list semantics unknown | The feasibility review found it contains duplicate player entries (per-trick). The `rounds` property sums them. Tests verify by checking round deltas sum to cumulative totals. |
| All-pass rounds are common (~46% in test data) | Handled explicitly in the internal model and mapped to a dedicated client type (`COMPLETED_NO_BIDDERS`). Test scenarios cover this. |
| Replay performance for long games | Same cost as existing `Game.events`. The `rounds` property is an independent replay, not additive. Acceptable for a read endpoint. |
| Discriminated union with multiple Literal values on one model | Pydantic v2 supports `Literal["BIDDING", "TRUMP_SELECTION", "DISCARD", "TRICKS"]` mapping to one model in a discriminated union. Verify during U2 implementation. |

---

## Sources & References

- **Origin document:** [docs/brainstorms/spike-game-read-requirements.md](docs/brainstorms/spike-game-read-requirements.md)
- Related plan: `docs/plans/2026-04-10-002-refactor-event-derivation-replay-plan.md` (the event-derivation refactor this builds on)
- Related learning: `docs/solutions/logic-errors/round-start-hands-lost-to-in-place-mutation-2026-04-11.md`
- UI mockup: `mockup.svg` (repo root)
