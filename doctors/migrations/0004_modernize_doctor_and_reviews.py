from django.db import migrations, models


def convert_star_ratings(apps, schema_editor):
    Review = apps.get_model("doctors", "Review")
    for review in Review.objects.all():
        value = str(review.rating)
        review.rating = min(max(len(value), 1), 5)
        review.save(update_fields=["rating"])


class Migration(migrations.Migration):
    dependencies = [
        ("doctors", "0003_review"),
        ("patients", "0003_patient_profile_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="doctor",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="doctors/images/",
            ),
        ),
        migrations.AlterField(
            model_name="doctor",
            name="fee",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="doctor",
            name="meet_link",
            field=models.URLField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="doctor",
            name="user",
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE,
                related_name="doctor_profile",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="doctor",
            name="bio",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="doctor",
            name="is_accepting_patients",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="body",
            field=models.TextField(max_length=2000),
        ),
        migrations.RunPython(convert_star_ratings, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="review",
            name="rating",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")]
            ),
        ),
        migrations.AlterField(
            model_name="review",
            name="doctor",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="reviews",
                to="doctors.doctor",
            ),
        ),
        migrations.AlterField(
            model_name="review",
            name="reviewer",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="reviews",
                to="patients.patient",
            ),
        ),
        migrations.AlterModelOptions(
            name="review",
            options={"ordering": ["-created"]},
        ),
    ]
