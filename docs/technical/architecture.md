# Architecture

The system is a modular Django monolith.

Initial modules:

- `apps.common`: shared model bases and helpers.
- `apps.accounts`: custom user model and authentication support.
- `apps.core`: condominium, blocks, units, memberships, active tenant resolution, and permissions.
- `apps.audit`: audit trail for sensitive actions.
- `apps.dashboard`: simple syndic dashboard.

Multi-tenancy is row-based. Business tables carry `condominium_id` directly where practical. Read access should go through selectors and write access through services.

The active condominium is stored in the session and loaded into `request.condominium` by `ActiveCondominiumMiddleware`.
