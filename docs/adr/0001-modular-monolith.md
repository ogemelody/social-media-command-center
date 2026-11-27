# ADR 0001: Modular monolith

**Status:** Accepted — 2026-11-25

Build one React frontend, one FastAPI modular monolith, one PostgreSQL database, and one separate worker from the same backend package. This minimizes operational complexity while preserving explicit module and provider boundaries. Microservices and distributed infrastructure are deferred.
