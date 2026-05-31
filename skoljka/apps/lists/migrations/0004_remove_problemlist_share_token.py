from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("lists", "0003_remove_problemlist_group_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="problemlist",
            name="share_token",
        ),
    ]
