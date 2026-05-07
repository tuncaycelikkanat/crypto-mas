# ADR-0001: Database Session Strategy

## Status

Accepted for current phase, to be revisited before production-grade workers.

## Context

The system currently uses SQLAlchemy 2 with synchronous `create_engine` and `Session`.

Current development scope includes:

- FastAPI API endpoints
- PostgreSQL / TimescaleDB persistence
- Alembic migrations
- Repository pattern
- Market data persistence
- Feature pipeline
- Signal and scoring agents

In the future, the system will include higher I/O workloads:

- WebSocket market data collectors
- scheduled historical data ingestion
- paper trading loops
- live execution workers
- reconciliation workers
- reporting workers
- event consumers

For these workloads, asynchronous database access may improve throughput and reduce blocking behavior.

## Decision

For the current phase, the project will continue using synchronous SQLAlchemy sessions.

The main reasons are:

- simpler development and debugging
- lower implementation complexity
- easier repository and migration setup
- current workloads are low-frequency and not latency-sensitive
- the system is not yet running continuous ingestion or live execution workers

Before introducing production-grade workers, the database strategy will be revisited.

## Alternatives Considered

### Option 1: Continue with synchronous SQLAlchemy

Pros:

- simple
- stable
- easy to test
- compatible with current code
- sufficient for API, backtest prototypes and small paper trading flows

Cons:

- may block under high I/O
- less suitable for WebSocket-heavy ingestion
- may become a bottleneck in worker-based architecture

### Option 2: Switch fully to Async SQLAlchemy + asyncpg now

Pros:

- better fit for async collectors and workers
- non-blocking DB I/O
- future-ready for event-driven architecture

Cons:

- more complex session management
- more complex testing
- larger refactor now
- unnecessary for current low-frequency development phase

### Option 3: Hybrid model

Use synchronous DB sessions for admin/API and asynchronous sessions for ingestion/worker services.

Pros:

- practical separation
- high-I/O services can be async
- simple API code can remain sync

Cons:

- two DB access patterns
- duplicated infrastructure code
- higher cognitive overhead

## Current Approach

The current approach is:

- keep sync SQLAlchemy for now
- keep repository boundaries clean
- avoid leaking DB session logic into business logic
- revisit async migration before implementing:
  - WebSocket collectors
  - event consumers
  - live execution workers
  - reconciliation workers

## Future Migration Plan

If async DB is adopted later:

1. Introduce `AsyncSession` and `create_async_engine`.
2. Add async repository equivalents or migrate repositories gradually.
3. Use `asyncpg` as PostgreSQL driver.
4. Update FastAPI dependencies for async sessions.
5. Update tests to use async fixtures.
6. Keep Alembic migration flow unchanged where possible.
7. Validate performance under ingestion and paper trading workloads.

## Consequences

Positive:

- development remains fast
- current code remains simple
- architecture remains clean due to repository boundaries

Negative:

- a future async migration may be required
- worker architecture must be designed carefully to avoid DB bottlenecks

## Review Trigger

This decision must be reviewed before:

- implementing continuous WebSocket ingestion
- implementing Redis Streams consumers
- implementing live trading execution workers
- running paper trading continuously for multiple symbols