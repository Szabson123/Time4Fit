import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0017_userprofile_daily_water_goal_ml_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMacroProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gender', models.CharField(choices=[('male', 'Mężczyzna'), ('female', 'Kobieta')], max_length=10)),
                ('age', models.PositiveIntegerField()),
                ('weight_kg', models.DecimalField(decimal_places=2, max_digits=5)),
                ('height_cm', models.DecimalField(decimal_places=2, max_digits=5)),
                ('body_fat_percentage', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ('activity_level', models.CharField(choices=[('sedentary', 'Siedząca'), ('lightly_active', 'Lekko aktywna'), ('moderately_active', 'Umiarkowanie aktywny'), ('very_active', 'Bardzo aktywny')], max_length=20)),
                ('goal', models.CharField(choices=[('maintenance', 'Utrzymanie wagi'), ('reduction', 'Redukcja'), ('muscle_gain', 'Budowa mięśni')], max_length=20)),
                ('bmr', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('tdee', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('target_calories', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('target_protein_g', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('target_fat_g', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('target_carbohydrates_g', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='macro_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
