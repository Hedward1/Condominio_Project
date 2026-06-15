# Security

Security priorities:

1. Never leak data between condominiums.
2. Enforce permissions in backend services and views.
3. Store no secrets in source code.
4. Log sensitive actions with `AuditLog`.
5. Keep uploaded files protected by backend authorization when document features are implemented.

Production settings force secure cookies, SSL redirect, HSTS, and require an explicit `DJANGO_SECRET_KEY`.
