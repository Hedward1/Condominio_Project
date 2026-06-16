from django import forms

from .models import ReservationStatus
from .selectors import list_amenities_for_condominium


class AmenityForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=120)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)
    rules = forms.CharField(label="Regras", required=False, widget=forms.Textarea)


class ReservationRequestForm(forms.Form):
    amenity = forms.ModelChoiceField(label="Area comum", queryset=None)
    start_at = forms.DateTimeField(
        label="Inicio",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    end_at = forms.DateTimeField(
        label="Fim",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    notes = forms.CharField(label="Observacoes", required=False, widget=forms.Textarea)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amenity"].queryset = list_amenities_for_condominium(
            condominium=condominium,
        )


class ReservationDecisionForm(forms.Form):
    manager_notes = forms.CharField(label="Observacoes do gestor", required=False, widget=forms.Textarea)


class ReservationAdminFilterForm(forms.Form):
    status = forms.ChoiceField(
        label="Status",
        choices=[("", "Todos")] + list(ReservationStatus.choices),
        required=False,
    )
    amenity = forms.ModelChoiceField(label="Area comum", queryset=None, required=False)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amenity"].queryset = list_amenities_for_condominium(
            condominium=condominium,
        )
