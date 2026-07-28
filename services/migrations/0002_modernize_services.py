from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="name",
            field=models.CharField(max_length=80),
        ),
        migrations.AlterField(
            model_name="service",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="services/image/",
            ),
        ),
        migrations.AlterModelOptions(
            name="service",
            options={"ordering": ["name"]},
        ),
    ]
