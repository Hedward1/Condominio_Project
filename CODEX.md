# Codex Manual

This project follows the condominium system rules defined in:

- `Base_documenation/CODEX_MANUAL_CONDOMINIO.md`
- `Base_documenation/Planejamento de Produto - Sistema Modular de Administracao de Condominios.pdf`

Mandatory working rules:

1. Keep the MVP scope limited to core, official communication, tickets, documents, reservations, and a simple syndic dashboard.
2. Every operational business object must be scoped to a condominium.
3. Business queries must filter by condominium or by a tenant-safe selector.
4. Backend permissions are mandatory.
5. Sensitive actions must create audit logs.
6. Do not implement boleto, banking, delinquency, formal assemblies, native app, full gatehouse, or advanced AI in the MVP.
7. Use services for writes and selectors for reads.
8. Add or update relevant tests for every change.
