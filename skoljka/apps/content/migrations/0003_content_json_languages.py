from django.db import migrations, models


def forwards(apps, schema_editor):
    Content = apps.get_model("content", "Content")
    ContentVersion = apps.get_model("content", "ContentVersion")

    grouped = {}
    for content in Content.objects.order_by("id"):
        key = (content.content_type_id, content.object_id)
        grouped.setdefault(key, []).append(content)

    for rows in grouped.values():
        primary = rows[0]
        texts = {}
        compiled = {}
        search_parts = []
        original_language = "en"
        try:
            model = primary.content_type.model_class()
            if model is not None:
                obj = model.objects.filter(pk=primary.object_id).first()
                original_language = getattr(obj, "original_language", None) or "en"
        except Exception:
            pass

        for row in rows:
            lang = row.language or original_language or "en"
            texts[lang] = row.source_md
            compiled[lang] = row.compiled_html
            if row.search_text:
                search_parts.append(row.search_text)

        primary.original_language = original_language
        primary.source_md_json = texts
        primary.compiled_html_json = compiled
        primary.search_text = " ".join(search_parts)
        primary.save(update_fields=["original_language", "source_md_json", "compiled_html_json", "search_text"])

        for duplicate in rows[1:]:
            duplicate.delete()

    for version in ContentVersion.objects.order_by("id"):
        lang = getattr(version.content, "original_language", "") or "en"
        version.source_md_json = {lang: version.source_md}
        version.save(update_fields=["source_md_json"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("content", "0002_contentattachment"),
        ("problems", "0004_remove_problem_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="content",
            name="original_language",
            field=models.CharField(default="en", max_length=10),
        ),
        migrations.AddField(
            model_name="content",
            name="source_md_json",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="content",
            name="compiled_html_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="contentversion",
            name="source_md_json",
            field=models.JSONField(default=dict),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="content",
            name="unique_content_per_object_language",
        ),
        migrations.RemoveField(
            model_name="content",
            name="language",
        ),
        migrations.RemoveField(
            model_name="content",
            name="source_md",
        ),
        migrations.RemoveField(
            model_name="content",
            name="compiled_html",
        ),
        migrations.RemoveField(
            model_name="contentversion",
            name="source_md",
        ),
        migrations.RenameField(
            model_name="content",
            old_name="source_md_json",
            new_name="source_md",
        ),
        migrations.RenameField(
            model_name="content",
            old_name="compiled_html_json",
            new_name="compiled_html",
        ),
        migrations.RenameField(
            model_name="contentversion",
            old_name="source_md_json",
            new_name="source_md",
        ),
        migrations.AddConstraint(
            model_name="content",
            constraint=models.UniqueConstraint(fields=("content_type", "object_id"), name="unique_content_per_object"),
        ),
    ]
