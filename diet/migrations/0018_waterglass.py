from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('diet', '0017_dailymealcalendar_water_intake_ml'),
    ]

    operations = [
        migrations.CreateModel(
            name='WaterGlass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_ml', models.PositiveIntegerField(help_text='Ilość w ml (np. 250)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('calendar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='water_glasses', to='diet.dailymealcalendar')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
