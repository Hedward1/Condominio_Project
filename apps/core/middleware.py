from .models import Condominium, CondominiumMembership

ACTIVE_CONDOMINIUM_SESSION_KEY = "active_condominium_id"


class ActiveCondominiumMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.condominium = None
        request.condominium_membership = None

        user = getattr(request, "user", None)
        active_id = request.session.get(ACTIVE_CONDOMINIUM_SESSION_KEY)

        if user is not None and user.is_authenticated and active_id:
            if user.is_superuser:
                request.condominium = Condominium.active_objects.filter(id=active_id).first()
            else:
                membership = (
                    CondominiumMembership.active_objects.select_related("condominium")
                    .filter(
                        condominium_id=active_id,
                        condominium__is_active=True,
                        user=user,
                    )
                    .first()
                )
                if membership is not None:
                    request.condominium = membership.condominium
                    request.condominium_membership = membership

            if request.condominium is None:
                request.session.pop(ACTIVE_CONDOMINIUM_SESSION_KEY, None)

        return self.get_response(request)
