from django import forms

from .selectors import list_categories_for_condominium


class AnnouncementCategoryForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=120)
    description = forms.CharField(label="Descricao", required=False, widget=forms.Textarea)


class AnnouncementForm(forms.Form):
    category = forms.ModelChoiceField(label="Categoria", queryset=None, required=False)
    title = forms.CharField(label="Titulo", max_length=180)
    content = forms.CharField(label="Conteudo", widget=forms.Textarea)
    is_pinned = forms.BooleanField(label="Fixado", required=False)

    def __init__(self, *args, condominium, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = list_categories_for_condominium(
            condominium=condominium,
        )
