from django.db import migrations, models


def null_labels_to_empty(apps, schema_editor):
    Problem = apps.get_model("problems", "Problem")
    Problem.objects.filter(problem_label__isnull=True).update(problem_label="")


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0005_remove_problem_original_language"),
    ]

    operations = [
        migrations.RenameField(
            model_name="problem",
            old_name="problem_number",
            new_name="problem_label",
        ),
        migrations.AlterField(
            model_name="problem",
            name="problem_label",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.RunPython(null_labels_to_empty, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="problem",
            name="problem_label",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterModelOptions(
            name="problem",
            options={"ordering": ["source", "year", "problem_label"]},
        ),
    ]
