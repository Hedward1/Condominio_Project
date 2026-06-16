from django import forms

from apps.core.selectors import list_membership_users_for_condominium, list_units_for_condominium

from .models import TicketPriority, TicketStatus
from .selectors import list_ticket_categories_for_condominium


class TicketCategoryForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=120)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)


class TicketCreateForm(forms.Form):
    category = forms.ModelChoiceField(label="Categoria", queryset=None, required=False)
    unit = forms.ModelChoiceField(label="Unidade", queryset=None, required=False)
    priority = forms.ChoiceField(label="Prioridade", choices=TicketPriority.choices)
    title = forms.CharField(label="Titulo", max_length=180)
    description = forms.CharField(label="Descricao", widget=forms.Textarea)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = list_ticket_categories_for_condominium(
            condominium=condominium,
        )
        self.fields["unit"].queryset = list_units_for_condominium(condominium=condominium)
        self.fields["priority"].initial = TicketPriority.NORMAL


class TicketAdminUpdateForm(forms.Form):
    status = forms.ChoiceField(label="Status", choices=TicketStatus.choices)
    priority = forms.ChoiceField(label="Prioridade", choices=TicketPriority.choices)
    assigned_to = forms.ModelChoiceField(label="Responsavel", queryset=None, required=False)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = list_membership_users_for_condominium(
            condominium=condominium,
        )


class TicketCommentForm(forms.Form):
    message = forms.CharField(label="Comentario", widget=forms.Textarea)
    is_internal = forms.BooleanField(label="Comentario interno", required=False)

    def __init__(self, *args, allow_internal=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not allow_internal:
            self.fields.pop("is_internal")
