from django.db import migrations


def forwards(apps, schema_editor):
    from skoljka.utils.markdown import compile_markdown

    Content = apps.get_model("content", "Content")
    ContentAttachment = apps.get_model("content", "ContentAttachment")

    for content in Content.objects.order_by("id"):
        attachments = ContentAttachment.objects.filter(content_id=content.pk)
        attachment_urls = {a.name: a.file.url for a in attachments if a.file}
        compiled = {}
        search_parts = []
        for lang, source in content.source_md.items():
            html, text = compile_markdown(source, attachment_urls=attachment_urls)
            compiled[lang] = html
            if text:
                search_parts.append(text)
        content.compiled_html = compiled
        content.search_text = " ".join(search_parts)
        content.save(update_fields=["compiled_html", "search_text"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("content", "0006_rerender_compiled_html_with_latex_text_extensions"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
