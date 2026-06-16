from django.db.models import Count
from django.utils import timezone

from apps.communication.models import Announcement, AnnouncementReadReceipt, AnnouncementStatus
from apps.core.models import CondominiumMembership, CondominiumRole, Unit
from apps.documents.models import Document
from apps.tickets.models import Ticket, TicketStatus

RESIDENT_SUMMARY_ROLES = [
    CondominiumRole.RESIDENT,
    CondominiumRole.OWNER,
    CondominiumRole.TENANT,
]


def get_syndic_dashboard_summary(*, condominium) -> dict:
    now = timezone.localtime()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    published_announcements = Announcement.active_objects.filter(
        condominium=condominium,
        status=AnnouncementStatus.PUBLISHED,
    )
    published_this_month = published_announcements.filter(published_at__gte=start_of_month).count()
    active_memberships = CondominiumMembership.active_objects.filter(condominium=condominium)
    active_member_count = active_memberships.count()
    published_count = published_announcements.count()
    possible_reads = published_count * active_member_count
    actual_reads = (
        AnnouncementReadReceipt.objects.filter(
            condominium=condominium,
            announcement__in=published_announcements,
            user__condominium_memberships__condominium=condominium,
            user__condominium_memberships__is_active=True,
        )
        .aggregate(total=Count("id", distinct=True))
        .get("total")
        or 0
    )
    tickets = Ticket.active_objects.filter(condominium=condominium)

    return {
        "total_units": Unit.active_objects.filter(condominium=condominium).count(),
        "active_residents": active_memberships.filter(
            condominium=condominium,
            role__in=RESIDENT_SUMMARY_ROLES,
        ).count(),
        "published_announcements_this_month": published_this_month,
        "announcement_read_rate": round((actual_reads / possible_reads) * 100) if possible_reads else 0,
        "open_tickets": tickets.filter(status=TicketStatus.OPEN).count(),
        "tickets_in_progress": tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
        "tickets_resolved_this_month": tickets.filter(
            status=TicketStatus.RESOLVED,
            resolved_at__gte=start_of_month,
        ).count(),
        "active_documents": Document.active_objects.filter(condominium=condominium).count(),
    }
