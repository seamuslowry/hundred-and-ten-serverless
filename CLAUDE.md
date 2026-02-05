# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Azure Functions REST API for the card game "Hundred and Ten" (110). Uses the `hundredandten` library (v2 from feat/v2 branch) for game logic, with this repo adding lobby management, persistence, and HTTP endpoints.

## Commands

```bash
# Local development (MongoDB + API on localhost:7071)
docker compose up -d --build

# Run tests (requires docker-compose.test.yml)
docker compose -f docker-compose.test.yml up --build

# Manual commands (if deps installed locally)
pytest tests                    # Run all tests
pytest tests/functions/test_bid.py  # Single test file
ruff check utils tests          # Lint
black --check utils tests       # Format check
pyright                         # Type check
```

CI enforces 100% test coverage.

## Architecture

```
function_app.py          # All 18 HTTP endpoints with @catcher decorator
utils/
  models/                # Game, Person, User (wraps hundredandten library)
  services/              # GameService, UserService (MongoDB persistence)
  mappers/
    client/              # serialize/deserialize for API JSON
    db/                  # serialize/deserialize for MongoDB documents
  dtos/
    client.py            # TypedDict DTOs for API responses
    db.py                # TypedDict DTOs for MongoDB documents
  decorators/            # @catcher converts exceptions to 400 responses
  parsers/               # parse_request() extracts identity + loads game
  constants.py           # Accessibility, GameRole, GameStatus enums
tests/
  helpers.py             # build_request(), read_response_body() utilities
```

## Key Patterns

**Request flow**: Request → `parse_request(req)` extracts user identity from Azure headers (`x-ms-client-principal-id`) and loads game → modify via hundredandten library → `GameService.save()` → `serialize.game()` for response.

**Event tracking**: `initial_event_knowledge = len(game.events)` before changes, passed to `serialize.game()` to return only new events.

**Testing endpoints**: Unwrap decorated functions via `.build().get_user_function()`:
```python
from function_app import create_game as wrapped
create_game = wrapped.build().get_user_function()
```

**Game states**: `WAITING_FOR_PLAYERS` (lobby) → `PLAYING` (RoundStatus from hundredandten) → `WON`

## Tech Stack

- Python 3.11+, Azure Functions, MongoDB (PyMongo), hundredandten v2
- Linting: ruff, black, pylint, pyright
- Testing: pytest, coverage
