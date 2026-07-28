from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contact_us", "0002_alter_contactus_options"),
    ]

    operations = [
        migrations.RenameField(
            model_name="contactus",
            old_name="Problem",
            new_name="problem",
        ),
        migrations.AlterField(
            model_name="contactus",
            name="name",
            field=models.CharField(max_length=80),
        ),
        migrations.AlterField(
            model_name="contactus",
            name="phone",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name="contactus",
            name="problem",
            field=models.TextField(max_length=3000),
        ),
        migrations.AddField(
            model_name="contactus",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="contactus",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="contactus",
            name="resolved",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name="contactus",
            options={
                "ordering": ["-created_at"],
                "verbose_name_plural": "Contact Us",
            },
        ),
    ]
