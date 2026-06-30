from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_alter_booking_estado'),
    ]

    operations = [
        migrations.DeleteModel(name='CapacidadeSemanal'),
        migrations.CreateModel(
            name='CapacidadeSemanal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('semana', models.DateField(unique=True)),
                ('vagas_total', models.PositiveIntegerField(default=10)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Capacidade Semanal',
                'verbose_name_plural': 'Capacidades Semanais',
                'ordering': ['semana'],
            },
        ),
    ]
