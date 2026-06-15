from apps.core.models import CondominiumMembership, CondominiumRole, Unit

RESIDENT_SUMMARY_ROLES = [
    CondominiumRole.RESIDENT,
    CondominiumRole.OWNER,
    CondominiumRole.TENANT,
]


def get_syndic_dashboard_summary(*, condominium) -> dict:
    return {
        "total_units": Unit.active_objects.filter(condominium=condominium).count(),
        "active_residents": CondominiumMembership.active_objects.filter(
            condominium=condominium,
            role__in=RESIDENT_SUMMARY_ROLES,
        ).count(),
    }
