class BusinessRuleViolation(Exception):
    """Raised when a domain rule blocks an operation."""


class TenantScopeViolation(Exception):
    """Raised when an object relation crosses condominium boundaries."""
