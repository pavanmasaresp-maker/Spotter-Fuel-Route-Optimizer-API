from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="GeocodeCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query", models.CharField(max_length=500, unique=True)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("display_name", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="RouteCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cache_key", models.CharField(max_length=64, unique=True)),
                ("payload", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
