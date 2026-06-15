# ADR 0002: Row-Based Multi-Tenancy

## Context

Every condominium must be isolated, but the MVP should avoid complex infrastructure.

## Decision

Use row-based multi-tenancy with `condominium_id` on business tables.

## Alternatives Considered

- One schema per tenant.
- One database per tenant.
- Subdomain-only isolation.

## Consequences

Queries must always be scoped by condominium. Selectors and services centralize this rule, and tests must verify cross-tenant access is blocked.
