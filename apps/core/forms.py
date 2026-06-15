from django import forms
from django.contrib.auth import get_user_model

from .models import CondominiumMembership, CondominiumRole
from .selectors import list_blocks_for_condominium


class BlockForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=120)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)


class UnitForm(forms.Form):
    block = forms.ModelChoiceField(label="Bloco", queryset=None, required=False)
    number = forms.CharField(label="Numero", max_length=40)
    floor = forms.CharField(label="Andar", max_length=20, required=False)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["block"].queryset = list_blocks_for_condominium(condominium=condominium)


class MembershipCreateForm(forms.Form):
    ALLOWED_ROLES = (
        CondominiumRole.COUNCIL,
        CondominiumRole.STAFF,
        CondominiumRole.RESIDENT,
        CondominiumRole.OWNER,
        CondominiumRole.TENANT,
    )

    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="E-mail")
    username = forms.CharField(label="Usuario", max_length=150, required=False)
    temporary_password = forms.CharField(
        label="Senha temporaria",
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )
    role = forms.ChoiceField(
        label="Papel",
        choices=[(role.value, role.label) for role in ALLOWED_ROLES],
    )

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.condominium = condominium
        self.existing_user = None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        User = get_user_model()
        self.existing_user = User.objects.filter(email__iexact=email).first()
        if self.existing_user is not None:
            already_member = CondominiumMembership.active_objects.filter(
                condominium=self.condominium,
                user=self.existing_user,
            ).exists()
            if already_member:
                raise forms.ValidationError("Este usuario ja e membro ativo deste condominio.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if username:
            User = get_user_model()
            existing = User.objects.filter(username__iexact=username).first()
            if existing is not None and (
                self.existing_user is None or existing.id != self.existing_user.id
            ):
                raise forms.ValidationError("Ja existe um usuario com este login.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        if self.existing_user is None:
            if not cleaned_data.get("username"):
                self.add_error("username", "Informe um usuario para novo cadastro.")
            if not cleaned_data.get("temporary_password"):
                self.add_error("temporary_password", "Informe uma senha temporaria.")
        return cleaned_data
