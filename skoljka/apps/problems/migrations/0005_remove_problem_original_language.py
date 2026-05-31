from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0004_remove_problem_slug"),
        ("content", "0003_content_json_languages"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="problem",
            name="original_language",
        ),
    ]
