from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from skoljka.apps.content.models import Content, ContentAttachment
from skoljka.utils.staff import staff_required


def _attachment_payload(attachment: ContentAttachment) -> dict[str, object]:
    return {
        "name": attachment.name,
        "url": attachment.file.url,
        "is_image": attachment.mime_type.startswith("image/"),
    }


@require_POST
@staff_required
def attachment_upload(request: HttpRequest, content_id: int) -> JsonResponse:
    content = get_object_or_404(Content, pk=content_id)
    uploads = request.FILES.getlist("files")
    if not uploads:
        return JsonResponse({"error": _("No files uploaded.")}, status=400)

    attachments = [ContentAttachment.from_upload(content, upload) for upload in uploads]
    content.save()
    return JsonResponse({"attachments": [_attachment_payload(a) for a in attachments]})


@require_http_methods(["DELETE"])
@staff_required
def attachment_delete(request: HttpRequest, content_id: int, name: str) -> JsonResponse:
    attachment = get_object_or_404(ContentAttachment, content_id=content_id, name=name)
    content = attachment.content
    attachment.file.delete(save=False)
    attachment.delete()
    content.save()
    return JsonResponse({"ok": True, "name": name})
