from django.db import migrations, models
import django.db.models.deletion
import skoljka.apps.content.models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to=skoljka.apps.content.models._attachment_upload_to)),
                ("mime_type", models.CharField(blank=True, max_length=100)),
                ("size", models.PositiveIntegerField(default=0)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("content", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="content.content")),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="contentattachment",
            constraint=models.UniqueConstraint(fields=("content", "name"), name="unique_attachment_name_per_content"),
        ),
    ]
