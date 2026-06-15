# Testing

The test suite uses `pytest` and `pytest-django`.

Required test categories:

- Tenant isolation.
- Backend permissions.
- Service business rules.
- Selectors scoped by condominium.
- Audit logs for sensitive actions.

Run locally:

```powershell
.\.venv\Scripts\python -m pytest
```
