---
title: "Recovering initial dealt hands via EngineRound reconstruction"
date: 2026-04-24
category: best-practices
module: src/models/internal/game.py
problem_type: best_practice
component: service_object
severity: medium
applies_when:
  - Reading round data directly from engine.rounds rather than via action-walking replay
  - You need pre-discard (initially dealt) hands but the engine mutates hands in-place during discards
  - Refactoring away from a separate replay engine instance to reduce per-call overhead
tags:
  - engine-integration
  - rounds
  - initial-hands
  - reconstruction
  - in-place-mutation
  - refactor
---

# Recovering initial dealt hands via EngineRound reconstruction

## Context

The engine (`hundredandten-engine`) tracks completed rounds cumulatively on `engine.rounds`. Reading directly from this list is simpler and cheaper than constructing a fresh `Engine` and replaying every action from scratch on each `rounds` call.

However, the engine mutates `RoundPlayer.hand` in-place during the discard phase. By the time a round is complete, `game_round.players[i].hand` reflects the post-discard state — the initially dealt cards are gone. Any feature that needs to show a player's starting hand (for history, events, or the round-based API) cannot simply read `game_round.players[i].hand` from a finished round.

The action-walking replay worked around this by snapshotting hands at round-start during the replay. Once that replay was removed in favour of direct engine inspection, a lighter-weight technique was needed.

## Guidance

Construct a fresh `EngineRound` using the same three deterministic inputs that produced the original round — players, dealer, and seed — and read hands from that pristine instance before any mutations have occurred.

```python
from hundredandten.engine.round import Round as EngineRound

def __get_round_at(self, round_index: int) -> Round:
    game_round = self._engine.rounds[round_index]

    # Reconstruct the round's initial state to recover pre-discard hands.
    # game_round.players[i].hand is post-discard; EngineRound with the same
    # players/dealer/seed reproduces the original deal deterministically.
    recreated_round = EngineRound(
        game_players=[EnginePlayer(p.identifier) for p in game_round.players],
        dealer_identifier=game_round.dealer.identifier,
        seed=game_round.deck.seed,  # TODO: have the engine expose round seed directly
    )

    return Round(
        dealer_player_id=game_round.dealer.identifier,
        trump=CardSuit[game_round.trump.name] if game_round.trump else None,
        initial_hands={
            p.identifier: [Card.from_engine(c) for c in p.hand]
            for p in recreated_round.players  # pristine, pre-discard hands
        },
        bid_history=[Bid.from_engine(b) for b in game_round.bids],
        discards={
            d.identifier: [Card.from_engine(c) for c in d.cards]
            for d in game_round.discards
        },
        tricks=[...],  # abbreviated — see src/models/internal/game.py for full Trick construction
        scores=round_scores,
    )

@property
def rounds(self) -> list[Round]:
    return [self.__get_round_at(i) for i in range(len(self._engine.rounds))]
```

Three properties make this safe:

1. **Determinism**: `EngineRound` dealing is seeded — the same `(players, dealer, seed)` always produces the same hand distribution.
2. **Isolation**: The fresh `EngineRound` has no actions applied, so `p.hand` is the original dealt state.
3. **Seed availability**: `game_round.deck.seed` carries the round's seed on a completed round. A future engine improvement would expose this as a first-class property on `EngineRound`.

**Active round current hand is different**: for the *active* round, use `game.get_player_in_round(player_id)` which correctly reflects post-discard state for ongoing play. `initial_hands` is for history/display; `get_player_in_round` is for game actions.

## Why This Matters

Without this technique, removing the action-walking replay loses access to initial dealt hands entirely. The options are:

- **Keep the full replay**: Expensive (constructs a whole `Engine`, replays every action, detects all boundaries) just to snapshot hand state at each round start.
- **Read post-discard hands**: Silently serves wrong data to the history/events feed.
- **`EngineRound` reconstruction**: Scoped to one round at a time, costs only the initial deal (no action replay), produces correct pre-discard hands.

## When to Apply

- You need pre-discard hand state for a completed round and the engine has already mutated hands in-place.
- You are reading round data from `engine.rounds` directly rather than maintaining a parallel replay engine.
- The engine's dealing is deterministic and seeded (true for current `hundredandten-engine`).
- You do **not** need this for the active round's current hand — `game.get_player_in_round()` covers that case.

## Examples

**Before — action-walking replay (pre-discard hands recovered as a side effect):**

```python
@property
def rounds(self) -> list[Round]:
    # Full engine replay just to snapshot hands at round start
    replay_engine = Engine(
        players=[EnginePlayer(p.id) for p in self.ordered_players],
        seed=self.seed,
    )
    # snapshot initial hands immediately after construction
    current_round = Round(
        dealer=replay_engine.active_round.dealer.identifier,
        hands={p.identifier: [...] for p in replay_engine.active_round.players},
    )
    for action in self.actions:
        # walk every action, detect boundaries, accumulate state...
        ...
```

Cost: one full `Engine` construction + replay of all N actions on every `rounds` call.

**After — direct inspection + targeted `EngineRound` reconstruction:**

```python
def __get_round_at(self, round_index: int) -> Round:
    game_round = self._engine.rounds[round_index]
    recreated_round = EngineRound(
        game_players=[EnginePlayer(p.identifier) for p in game_round.players],
        dealer_identifier=game_round.dealer.identifier,
        seed=game_round.deck.seed,
    )
    return Round(
        dealer_player_id=game_round.dealer.identifier,
        trump=CardSuit[game_round.trump.name] if game_round.trump else None,
        initial_hands={p.identifier: [...] for p in recreated_round.players},
        # bid_history, discards, tricks, scores omitted for brevity
    )

@property
def rounds(self) -> list[Round]:
    return [self.__get_round_at(i) for i in range(len(self._engine.rounds))]
```

Cost per call: one `EngineRound` construction per round (no action replay).

## Related

- `src/models/internal/game.py:300` — `Game.__get_round_at` and `Game.rounds`
- `src/models/internal/round.py` — `Round` model (`initial_hands`, `max_bid` property)
- [`docs/solutions/logic-errors/round-start-hands-lost-to-in-place-mutation-2026-04-11.md`](../logic-errors/round-start-hands-lost-to-in-place-mutation-2026-04-11.md) — the original discovery of the in-place mutation problem; the action-walking replay described there is now superseded for `Game.rounds` by this `EngineRound` reconstruction technique (it remains in use for `Game.events`)
- [`docs/solutions/logic-errors/game-rounds-action-replay-boundary-and-score-aggregation-bugs-2026-04-24.md`](../logic-errors/game-rounds-action-replay-boundary-and-score-aggregation-bugs-2026-04-24.md) — documents bugs in the action-walking replay approach that this technique replaces for `Game.rounds`
