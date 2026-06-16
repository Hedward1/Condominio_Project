from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.communication.models import Announcement, AnnouncementCategory, AnnouncementStatus
from apps.communication.services import create_announcement, create_category, publish_announcement
from apps.core.models import (
    Block,
    Condominium,
    CondominiumMembership,
    CondominiumRole,
    OccupancyType,
    Unit,
    UnitOccupancy,
)
from apps.core.services import (
    add_membership,
    create_block,
    create_condominium,
    create_unit,
    create_unit_occupancy,
)
from apps.documents.models import Document, DocumentCategory, DocumentVisibility
from apps.documents.services import create_document, create_document_category
from apps.reservations.models import Amenity, Reservation, ReservationStatus
from apps.reservations.services import approve_reservation, create_amenity, request_reservation
from apps.tickets.models import Ticket, TicketCategory, TicketPriority
from apps.tickets.services import create_ticket, create_ticket_category


class Command(BaseCommand):
    help = "Cria um condominio demo idempotente para apresentacao do MVP."

    def add_arguments(self, parser):
        parser.add_argument("--slug", default="condominio-demo")
        parser.add_argument("--password", default="Demo@12345")

    def handle(self, *args, **options):
        slug = options["slug"]
        password = options["password"]

        syndic = self._ensure_user(
            username="sindico_demo",
            email="sindico.demo@example.com",
            password=password,
            first_name="Sindico",
            last_name="Demo",
        )
        resident = self._ensure_user(
            username="morador_demo",
            email="morador.demo@example.com",
            password=password,
            first_name="Morador",
            last_name="Demo",
        )

        condominium = Condominium.active_objects.filter(slug=slug).first()
        if condominium is None:
            condominium = create_condominium(
                name="Condominio Demo",
                slug=slug,
                actor=syndic,
                address="Rua Demo, 100",
                city="Sao Paulo",
                state="SP",
                postal_code="01000-000",
            )
            self.stdout.write(self.style.SUCCESS("Condominio demo criado."))
        else:
            self.stdout.write("Condominio demo ja existia; reutilizando dados.")

        self._ensure_membership(
            condominium=condominium,
            actor=syndic,
            user=syndic,
            role=CondominiumRole.SYNDIC,
        )
        self._ensure_membership(
            condominium=condominium,
            actor=syndic,
            user=resident,
            role=CondominiumRole.RESIDENT,
        )

        block = self._ensure_block(condominium=condominium, actor=syndic)
        unit = self._ensure_unit(condominium=condominium, actor=syndic, block=block)
        self._ensure_occupancy(
            condominium=condominium,
            actor=syndic,
            unit=unit,
            user=resident,
        )
        self._ensure_announcement(condominium=condominium, actor=syndic)
        self._ensure_ticket(condominium=condominium, actor=resident, manager=syndic, unit=unit)
        self._ensure_document(condominium=condominium, actor=syndic)
        self._ensure_reservation(condominium=condominium, actor=resident, manager=syndic)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed demo concluida."))
        self.stdout.write(f"Condominio: {condominium.name} ({condominium.slug})")
        self.stdout.write(f"Sindico: sindico.demo@example.com / {password}")
        self.stdout.write(f"Morador: morador.demo@example.com / {password}")
        self.stdout.write(
            self.style.WARNING(
                "Use --password para definir uma senha propria em ambientes compartilhados.",
            ),
        )

    def _ensure_user(self, *, username, email, password, first_name, last_name):
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            return user

        changed = False
        if not user.is_active:
            user.is_active = True
            changed = True
        for field, value in {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        }.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed = True
        if not user.has_usable_password() or not user.check_password(password):
            user.set_password(password)
            changed = True
        if changed:
            user.full_clean()
            user.save()
        return user

    def _ensure_membership(self, *, condominium, actor, user, role):
        membership = CondominiumMembership.active_objects.filter(
            condominium=condominium,
            user=user,
        ).first()
        if membership is not None:
            return membership

        if CondominiumMembership.active_objects.filter(condominium=condominium, user=actor).exists():
            return add_membership(
                condominium=condominium,
                actor=actor,
                user=user,
                role=role,
            )

        return CondominiumMembership.objects.create(
            condominium=condominium,
            user=user,
            role=role,
            invited_by=actor,
            created_by=actor,
            updated_by=actor,
        )

    def _ensure_block(self, *, condominium, actor):
        block = Block.active_objects.filter(condominium=condominium, name="Bloco A").first()
        if block is not None:
            return block
        return create_block(
            condominium=condominium,
            actor=actor,
            name="Bloco A",
            description="Bloco principal do condominio demo.",
        )

    def _ensure_unit(self, *, condominium, actor, block):
        unit = Unit.active_objects.filter(
            condominium=condominium,
            block=block,
            number="101",
        ).first()
        if unit is not None:
            return unit
        return create_unit(
            condominium=condominium,
            actor=actor,
            block=block,
            number="101",
            floor="1",
            description="Unidade demo.",
        )

    def _ensure_occupancy(self, *, condominium, actor, unit, user):
        occupancy = UnitOccupancy.active_objects.filter(
            condominium=condominium,
            unit=unit,
            user=user,
            occupancy_type=OccupancyType.RESIDENT,
        ).first()
        if occupancy is not None:
            return occupancy
        return create_unit_occupancy(
            condominium=condominium,
            actor=actor,
            unit=unit,
            user=user,
            occupancy_type=OccupancyType.RESIDENT,
            is_primary=True,
        )

    def _ensure_announcement(self, *, condominium, actor):
        announcement_category = AnnouncementCategory.active_objects.filter(
            condominium=condominium,
            name="Avisos gerais",
        ).first()
        if announcement_category is None:
            announcement_category = create_category(
                condominium=condominium,
                actor=actor,
                name="Avisos gerais",
                description="Comunicados administrativos do condominio.",
            )

        announcement = Announcement.active_objects.filter(
            condominium=condominium,
            title="Bem-vindo ao portal do condominio",
        ).first()
        if announcement is None:
            announcement = create_announcement(
                condominium=condominium,
                actor=actor,
                category=announcement_category,
                title="Bem-vindo ao portal do condominio",
                content="Este e o mural oficial para comunicados, chamados, documentos e reservas.",
                is_pinned=True,
            )
        if announcement.status == AnnouncementStatus.DRAFT:
            announcement = publish_announcement(
                condominium=condominium,
                actor=actor,
                announcement=announcement,
            )
        return announcement

    def _ensure_ticket(self, *, condominium, actor, manager, unit):
        category = TicketCategory.active_objects.filter(
            condominium=condominium,
            name="Manutencao",
        ).first()
        if category is None:
            category = create_ticket_category(
                condominium=condominium,
                actor=manager,
                name="Manutencao",
                description="Demandas de manutencao predial.",
            )

        ticket = Ticket.active_objects.filter(
            condominium=condominium,
            title="Lampada queimada no corredor",
        ).first()
        if ticket is not None:
            return ticket
        return create_ticket(
            condominium=condominium,
            actor=actor,
            category=category,
            unit=unit,
            priority=TicketPriority.NORMAL,
            title="Lampada queimada no corredor",
            description="Lampada queimada no corredor do primeiro andar.",
        )

    def _ensure_document(self, *, condominium, actor):
        category = DocumentCategory.active_objects.filter(
            condominium=condominium,
            name="Normas",
        ).first()
        if category is None:
            category = create_document_category(
                condominium=condominium,
                actor=actor,
                name="Normas",
                description="Documentos normativos do condominio.",
            )

        document = Document.active_objects.filter(
            condominium=condominium,
            title="Regimento interno demo",
        ).first()
        if document is not None:
            return document

        uploaded_file = ContentFile(
            b"Regimento interno demo.\nUse este documento apenas para apresentacao.\n",
            name="regimento-interno-demo.txt",
        )
        uploaded_file.content_type = "text/plain"
        return create_document(
            condominium=condominium,
            actor=actor,
            category=category,
            title="Regimento interno demo",
            description="Documento de exemplo para demonstrar download protegido.",
            visibility=DocumentVisibility.PUBLIC_TO_RESIDENTS,
            uploaded_file=uploaded_file,
        )

    def _ensure_reservation(self, *, condominium, actor, manager):
        amenity = Amenity.active_objects.filter(
            condominium=condominium,
            name="Salao de festas",
        ).first()
        if amenity is None:
            amenity = create_amenity(
                condominium=condominium,
                actor=manager,
                name="Salao de festas",
                description="Espaco para eventos dos moradores.",
                rules="Reservas sujeitas a aprovacao do sindico.",
            )

        reservation = Reservation.active_objects.filter(
            condominium=condominium,
            amenity=amenity,
            requested_by=actor,
            status__in=[ReservationStatus.PENDING, ReservationStatus.APPROVED],
        ).first()
        if reservation is None:
            start_at = timezone.now() + timedelta(days=7)
            end_at = start_at + timedelta(hours=3)
            reservation = request_reservation(
                condominium=condominium,
                actor=actor,
                amenity=amenity,
                start_at=start_at,
                end_at=end_at,
                notes="Reserva demo para apresentacao.",
            )
        if reservation.status == ReservationStatus.PENDING:
            reservation = approve_reservation(
                condominium=condominium,
                actor=manager,
                reservation=reservation,
                manager_notes="Aprovado para demonstracao.",
            )
        return reservation
