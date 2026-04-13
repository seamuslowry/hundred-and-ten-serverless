# AGENTS.md

Repository map for AI agent sessions working on `hundred-and-ten-serverless`.

## Project Overview

A serverless API for the card game **Hundred and Ten** (a.k.a. One Hundred Ten). Built with FastAPI, deployed on Azure Functions, backed by MongoDB (CosmosDB in production). The core game logic lives in external packages (`hundredandten-engine`, `hundredandten-automation-naive`, `hundredandten-automation-engineadapter`) hosted on PyPI; this project is the API/persistence layer wrapping that engine.

## Tech Stack

| Layer           | Technology                                                   |
| --------------- | ------------------------------------------------------------ |
| Language        | Python 3.12+ (lint target: 3.14)                            |
| Framework       | FastAPI (ASGI) wrapped by Azure Functions `AsgiFunctionApp`  |
| Database        | MongoDB via Beanie ODM (async) / PyMongo                     |
| Auth            | Firebase ID tokens validated against Google public keys      |
| Game engine     | `hundredandten-engine` + `hundredandten-automation-naive` + `hundredandten-automation-engineadapter` (PyPI) |
| Package manager | uv                                                           |
| Linting         | pylint, pyright, ruff, black                                 |
| Testing         | pytest + pytest-asyncio, 100% branch coverage enforced       |
| IaC             | Terraform/OpenTofu (Azure)                                   |
| CI/CD           | GitHub Actions (lint, coverage, deploy-staging)               |

## Repository Layout

```
.
├── function_app.py              # Entrypoint: FastAPI lifespan + Azure ASGI wrapper
├── pyproject.toml               # Dependencies, tool config, build system
├── uv.lock                      # Lockfile
├── Dockerfile                   # Azure Functions Python 3.12 image
├── docker-compose.yml           # Local dev: MongoDB + Functions
├── docker-compose.test.yml      # Test-only: MongoDB container
├── host.json                    # Azure Functions host config
├── local.settings.json          # Local Azure Functions env vars
│
├── src/                         # Application source (src-layout)
│   ├── auth/                    # Firebase token validation + FastAPI dependencies
│   │   ├── depends.py           #   Bearer token -> Identity dependency injection
│   │   ├── firebase.py          #   Google public key fetch + JWT verification
│   │   └── identity.py          #   Identity dataclass (id, name, picture_url)
│   ├── models/                  # 3-tier model system
│   │   ├── client/              #   API-facing Pydantic models (requests + responses)
│   │   ├── internal/            #   Domain dataclasses (game, player, actions, errors)
│   │   └── db/                  #   Beanie Documents for MongoDB persistence
│   ├── mappers/                 # Bidirectional transformations between model tiers
│   │   ├── client/              #   Internal <-> API (serialize.py / deserialize.py)
│   │   └── db/                  #   Internal <-> DB (serialize.py / deserialize.py)
│   ├── routers/                 # FastAPI route handlers
│   │   ├── players.py           #   /players/{id} — login, refresh, search
│   │   ├── lobbies.py           #   /players/{id}/lobbies — create, join, start
│   │   └── games.py             #   /players/{id}/games — act, queue, events, search
│   └── services/                # Business logic + DB interaction
│       ├── player.py            #   PlayerService (save, search, lookup)
│       ├── lobby.py             #   LobbyService (save, search, start_game)
│       └── game.py              #   GameService (save, get, search)
│
├── tests/                       # Test suite (100% branch coverage)
│   ├── conftest.py              #   Root: FastAPI TestClient fixture
│   ├── helpers.py               #   Shared helpers (create lobby, start game, etc.)
│   ├── auth/                    #   Firebase + exception handler tests
│   ├── functions/               #   Integration tests (auto-mocked Firebase auth)
│   │   └── conftest.py          #   Bearer token value = user ID (mock)
│   └── mappers/                 #   Mapper edge case tests
│
├── .github/workflows/           # CI/CD
│   ├── lint.yaml                #   pylint + pyright + ruff + black
│   ├── coverage.yaml            #   pytest with 100% coverage gate
│   └── deploy-staging.yml       #   Azure staging slot deploy on push to main
│
├── .infrastructure/             # Terraform/OpenTofu (Azure resources)
│   ├── main.tf                  #   Provider config, resource group
│   ├── function.tf              #   Function App, App Service Plan, Storage
│   └── github.tf                #   OIDC federated identity for CI deploy
│
└── docs/                        # Project knowledge base
    ├── brainstorms/             #   Requirements docs from brainstorming sessions
    ├── plans/                   #   Dated implementation plans
    ├── solutions/               #   Solved problems (logic-errors, test-failures, best-practices)
    ├── design-docs/             #   Architectural design documents
    ├── learnings/               #   Cross-cutting lessons and patterns
    └── references/              #   External references, specs, vendor docs
```

## Architecture

### 3-Tier Model System

The codebase enforces strict separation between API, domain, and persistence models:

1. **Client models** (`src/models/client/`) — Pydantic models for request/response serialization
2. **Internal models** (`src/models/internal/`) — Frozen dataclasses for business logic; wrap the `hundredandten-engine`
3. **DB models** (`src/models/db/`) — Beanie Documents for MongoDB persistence

**Mappers** (`src/mappers/`) bridge between tiers. Each mapper directory has `serialize.py` (internal -> target) and `deserialize.py` (target -> internal).

### Request Flow

```
Client Request
  → Firebase auth (depends.py verifies Bearer token)
  → Router (thin: validates, delegates to service)
  → Service (DB operations via Beanie ODM)
  → Mapper (DB doc <-> Internal model)
  → Internal model (domain logic, engine interaction)
  → Mapper (Internal model -> Client response)
  → Client Response
```

### Game Lifecycle

```
Lobby (waiting for players)
  → start_game() converts Lobby document to Game document
  → Game (active play — bidding, trump selection, discarding, playing tricks)
  → Game with winner (completed)
```

### Key Domain Patterns

- **ActionRequest discriminated union** — `NoAction | ConcreteAction | RequestAutomation` dispatches player automation at the app layer, not the engine layer. See `src/models/internal/player.py`.
- **Action-walking replay** — `Game.events` reconstructs the full event log by replaying actions through a fresh engine instance, snapshotting state at round/trick boundaries. See `src/models/internal/game.py:204`.
- **All routes nested under `/players/{player_id}/`** — Firebase auth is enforced globally; the path player ID is verified against the token identity.
- **CPU auto-fill** — lobbies with fewer than 4 players get `NaiveCpu` players added at start time.

## Development Commands

```sh
# Local development
docker compose up -d --build          # Start MongoDB + Functions on :7071

# Tests (requires MongoDB — use docker-compose.test.yml)
docker compose -f docker-compose.test.yml up -d
uv run pytest                         # Run tests
uv run coverage run -m pytest         # Run with coverage
uv run coverage report --fail-under=100  # Enforce 100% branch coverage

# Linting
uv run pylint src tests function_app.py
uv run pyright
uv run ruff check .
uv run black --check .

# Formatting
uv run black .
uv run ruff check --fix .
```

## Quality Standards

- **100% branch coverage** — enforced in CI; no exceptions
- **Four linters** — pylint, pyright, ruff, black must all pass
- **Frozen dataclasses** for internal models — immutability by default
- **Discriminated unions** with exhaustive `match` + wildcard `case _: raise` arms
- **No engine types at service boundaries** — mappers handle all conversions

## Knowledge Base (`docs/`)

| Directory          | Purpose                                                                 |
| ------------------ | ----------------------------------------------------------------------- |
| `brainstorms/`     | Requirements documents from brainstorming sessions                      |
| `plans/`           | Dated implementation plans (`YYYY-MM-DD-NNN-type-description-plan.md`)  |
| `solutions/`       | Solved problems, organized by category (logic-errors, test-failures, best-practices) |
| `design-docs/`     | Architectural design documents and ADRs                                 |
| `learnings/`       | Cross-cutting lessons, patterns, and conventions                        |
| `references/`      | External references, specs, vendor documentation                        |

### Solution doc conventions

Solutions use YAML frontmatter with: `title`, `date`, `category`, `module`, `problem_type`, `component`, `severity`, `tags`, and optional `symptoms`, `root_cause`, `resolution_type`, `related_components`, `applies_when`.

## External Dependencies of Note

- **`hundredandten-engine`**, **`hundredandten-automation-naive`**, and **`hundredandten-automation-engineadapter`** are pinned in `pyproject.toml` and resolve from regular PyPI. A `[[tool.uv.index]]` entry for TestPyPI exists with `explicit = true` but is not currently used as a source for any of these packages.
- The engine mutates `RoundPlayer.hand` in-place during discards — the action-walking replay pattern exists specifically to work around this.
