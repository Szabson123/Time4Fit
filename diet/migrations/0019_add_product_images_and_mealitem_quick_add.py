from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diet', '0018_waterglass'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, help_text='Zdjęcie produktu', null=True, upload_to='products_images/'),
        ),
        migrations.AddField(
            model_name='product',
            name='ingredients_image',
            field=models.ImageField(blank=True, help_text='Zdjęcie składników z etykiety', null=True, upload_to='ingredients_images/'),
        ),
        migrations.AddField(
            model_name='mealitem',
            name='is_quick_add',
            field=models.BooleanField(default=False, help_text='True jeśli dodano przez szybkie dodawanie (snapshot bez produktu)'),
        ),
    ]
