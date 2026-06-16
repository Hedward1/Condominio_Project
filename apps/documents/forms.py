from django import forms

from .models import DocumentVisibility
from .selectors import list_document_categories_for_condominium


class DocumentCategoryForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=120)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)


class DocumentCreateForm(forms.Form):
    category = forms.ModelChoiceField(label="Categoria", queryset=None, required=False)
    title = forms.CharField(label="Titulo", max_length=180)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)
    visibility = forms.ChoiceField(label="Visibilidade", choices=DocumentVisibility.choices)
    file = forms.FileField(label="Arquivo")

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = list_document_categories_for_condominium(
            condominium=condominium,
        )
        self.fields["visibility"].initial = DocumentVisibility.PUBLIC_TO_RESIDENTS


class DocumentMetadataForm(forms.Form):
    category = forms.ModelChoiceField(label="Categoria", queryset=None, required=False)
    title = forms.CharField(label="Titulo", max_length=180)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)
    visibility = forms.ChoiceField(label="Visibilidade", choices=DocumentVisibility.choices)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = list_document_categories_for_condominium(
            condominium=condominium,
        )


class DocumentAdminFilterForm(forms.Form):
    visibility = forms.ChoiceField(
        label="Visibilidade",
        choices=[("", "Todas")] + list(DocumentVisibility.choices),
        required=False,
    )
    category = forms.ModelChoiceField(label="Categoria", queryset=None, required=False)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = list_document_categories_for_condominium(
            condominium=condominium,
        )
