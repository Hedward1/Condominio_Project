# ADR 0001: Django Modular Monolith

## Context

The MVP needs fast delivery, simple deployment, backend permissions, templates, and clear business rules.

## Decision

Use a modular Django monolith.

## Alternatives Considered

- Separate API and frontend SPA.
- Microservices.

## Consequences

The first version is easier to build, test, and deploy. Modules remain separated by Django apps so the system can evolve without premature operational complexity.
