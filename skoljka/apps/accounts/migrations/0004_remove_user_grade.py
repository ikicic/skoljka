from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_create_personal_groups"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="grade",
        ),
    ]
