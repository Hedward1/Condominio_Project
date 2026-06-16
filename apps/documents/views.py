from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from apps.core.permissions import (
    require_active_membership,
    require_condominium_manager,
    user_can_manage_condominium,
)

from .forms import DocumentCategoryForm, DocumentCreateForm, DocumentMetadataForm
from .selectors import (
    get_document_category_for_condominium,
    get_document_for_manager,
    get_document_for_resident,
    list_document_categories_for_condominium,
    list_documents_for_manager,
    list_documents_for_resident,
)
from .services import (
    create_document,
    create_document_category,
    deactivate_document,
    deactivate_document_category,
    record_document_download,
    update_document_category,
    update_document_metadata,
)


def _active_condominium_or_redirect(request):
    if request.condominium is None:
        return None, redirect("core:condominium_select")
    return request.condominium, None


def _add_validation_error(form, error):
    if hasattr(error, "error_dict"):
        for field, messages_list in error.message_dict.items():
            target_field = field if field in form.fields else None
            for message in messages_list:
                form.add_error(target_field, message)
        return
    if hasattr(error, "messages"):
        for message in error.messages:
            form.add_error(None, message)
        return
    form.add_error(None, str(error))


def _message_validation_error(request, error):
    messages.error(request, "; ".join(error.messages))


@login_required
def document_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_active_membership(request.user, condominium)

    return render(
        request,
        "documents/document_list.html",
        {"documents": list_documents_for_resident(condominium=condominium)},
    )


@login_required
def document_detail(request, document_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_active_membership(request.user, condominium)
    document = get_document_for_resident(condominium=condominium, document_id=document_id)

    return render(request, "documents/document_detail.html", {"document": document})


@login_required
def document_download(request, document_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response

    if user_can_manage_condominium(request.user, condominium):
        document = get_document_for_manager(condominium=condominium, document_id=document_id)
    else:
        require_active_membership(request.user, condominium)
        document = get_document_for_resident(condominium=condominium, document_id=document_id)

    record_document_download(
        condominium=condominium,
        actor=request.user,
        document=document,
        request=request,
    )

    if not document.file:
        raise Http404("Arquivo nao encontrado.")
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.original_filename,
        content_type=document.content_type or "application/octet-stream",
    )


@login_required
def admin_document_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "documents/admin_document_list.html",
        {"documents": list_documents_for_manager(condominium=condominium)},
    )


@login_required
def document_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = DocumentCreateForm(request.POST or None, request.FILES or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            document = create_document(
                condominium=condominium,
                actor=request.user,
                category=form.cleaned_data["category"],
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                visibility=form.cleaned_data["visibility"],
                uploaded_file=form.cleaned_data["file"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Documento cadastrado.")
            return redirect("documents:document_edit", document_id=document.id)

    return render(request, "documents/document_form.html", {"form": form})


@login_required
def document_edit(request, document_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    document = get_document_for_manager(condominium=condominium, document_id=document_id)

    form = DocumentMetadataForm(
        request.POST or None,
        condominium=condominium,
        initial={
            "category": document.category_id,
            "title": document.title,
            "description": document.description,
            "visibility": document.visibility,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_document_metadata(
                condominium=condominium,
                actor=request.user,
                document=document,
                category=form.cleaned_data["category"],
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                visibility=form.cleaned_data["visibility"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Documento atualizado.")
            return redirect("documents:admin_document_list")

    return render(
        request,
        "documents/document_form.html",
        {"form": form, "document": document, "is_update": True},
    )


@login_required
def document_deactivate(request, document_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    document = get_document_for_manager(condominium=condominium, document_id=document_id)

    if request.method == "POST":
        try:
            deactivate_document(condominium=condominium, actor=request.user, document=document)
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Documento desativado.")
            return redirect("documents:admin_document_list")

    return render(
        request,
        "core/deactivate_confirm.html",
        {
            "title": "Desativar documento",
            "object_label": document.title,
            "cancel_url_name": "documents:admin_document_list",
        },
    )


@login_required
def category_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "documents/category_list.html",
        {"categories": list_document_categories_for_condominium(condominium=condominium)},
    )


@login_required
def category_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = DocumentCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_document_category(
                condominium=condominium,
                actor=request.user,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Categoria cadastrada.")
            return redirect("documents:category_list")

    return render(request, "documents/category_form.html", {"form": form})


@login_required
def category_update(request, category_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    category = get_document_category_for_condominium(
        condominium=condominium,
        category_id=category_id,
    )

    form = DocumentCategoryForm(
        request.POST or None,
        initial={"name": category.name, "description": category.description},
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_document_category(
                condominium=condominium,
                actor=request.user,
                category=category,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Categoria atualizada.")
            return redirect("documents:category_list")

    return render(
        request,
        "documents/category_form.html",
        {"form": form, "is_update": True},
    )


@login_required
def category_deactivate(request, category_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    category = get_document_category_for_condominium(
        condominium=condominium,
        category_id=category_id,
    )

    if request.method == "POST":
        try:
            deactivate_document_category(
                condominium=condominium,
                actor=request.user,
                category=category,
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Categoria desativada.")
            return redirect("documents:category_list")

    return render(
        request,
        "core/deactivate_confirm.html",
        {
            "title": "Desativar categoria de documento",
            "object_label": category.name,
            "cancel_url_name": "documents:category_list",
        },
    )
