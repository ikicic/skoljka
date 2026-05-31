from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tags", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="descriptions",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
