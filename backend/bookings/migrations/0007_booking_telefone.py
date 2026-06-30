from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0006_cliente_booking_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='telefone',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
