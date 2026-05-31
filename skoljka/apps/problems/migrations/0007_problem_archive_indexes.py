from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0006_rename_problem_number_to_problem_label"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="problem",
            index=models.Index(fields=["source", "year"], name="problem_source_year_idx"),
        ),
        migrations.AddIndex(
            model_name="problem",
            index=models.Index(fields=["source", "year", "problem_label"], name="problem_source_year_label_idx"),
        ),
    ]
