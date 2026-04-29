from rest_framework import serializers
from .models import Booking
from django.utils.timezone import localtime


class BookingSerializer(serializers.ModelSerializer):

    data = serializers.DateTimeField()

    class Meta:
        model = Booking
        fields = ['id', 'nome', 'email', 'data', 'mensagem']
        read_only_fields = ['id']


    def validate_data(self, value):
        data_local = localtime(value)

        # 🔒 1. evitar duplicados
        if Booking.objects.filter(data=value).exists():
            raise serializers.ValidationError(
                "Já existe uma marcação para este horário."
            )

        # ⏰ 2. validar horário (9h–18h)
        if data_local.hour < 9 or data_local.hour > 18:
            raise serializers.ValidationError(
                "Horário fora do período permitido (9h–18h)."
            )

        # ⏱ 3. validar intervalos de 1h
        if data_local.minute != 0:
            raise serializers.ValidationError(
                "As marcações devem ser feitas em horas certas (ex: 10:00, 11:00)."
            )

        return value