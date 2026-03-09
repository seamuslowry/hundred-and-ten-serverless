# Learnings - Beanie Migration

This notepad captures conventions, patterns, and findings discovered during execution.

---

## Task 2: pytest-asyncio Setup (COMPLETED)

### Key Configuration Points
- **pytest-asyncio version**: 1.3.0 installed successfully
- **asyncio_mode = "auto"**: Enables automatic async test detection without per-function decorators
- **Installation method**: `pip install -e ".[test]"` properly resolves optional dependencies from pyproject.toml

### Implementation Details
1. Added `pytest-asyncio>=0.24.0` to `[project.optional-dependencies] test` section
2. Created new `[tool.pytest.ini_options]` configuration section with `asyncio_mode = "auto"`
3. Verification confirmed automatic discovery will work for async test functions

### Pattern Reference
The `[tool.pytest.ini_options]` section should be placed after other `[tool.*]` sections in pyproject.toml.

### Dependency Impact
This enables Tasks 8, 9, 10, 11 to use async test patterns without decorator boilerplate.

## Task 1: Configure Docker MongoDB as Replica Set

### Key Learnings

1. **Authentication Conflict**: MONGO_INITDB_ROOT_USERNAME/PASSWORD environment variables conflict with MongoDB replica set auth requirements. Removed environment variables for test environment since auth is not required.

2. **Network Binding**: MongoDB in Docker defaults to binding to 127.0.0.1. For container-to-container communication, added `--bind_ip_all` flag to mongod command to listen on all interfaces.

3. **Healthcheck Requirement**: The init-replica service depends on db service's healthcheck (condition: service_healthy). This ensures mongosh can connect before running rs.initiate().

4. **Replica Set Initialization**: Single-node replica set with `rs.initiate()` works without keyfile for unauthenticated deployments. The init script uses `|| true` to handle idempotence (safe to run multiple times).

5. **Data Persistence**: Replica set configuration survives container restart - volume mounts preserve the config.

### Implementation Details

- Docker-compose modification approach:
  - Added `--replSet rs0` and `--bind_ip_all` to mongod command
  - Created init-replica service that waits for db health check
  - Uses mongosh to execute `rs.initiate()` via shell script
  
- QA Validation:
  - Fresh start: rs.status().ok = 1 ✓
  - Restart persistence: rs.status().ok = 1 ✓

### Dependencies Met

- ✓ MongoDB replica set configured for transaction support
- ✓ Blocks: Tasks 6 (transaction), 8 (conftest), 12 (verification) can now proceed
