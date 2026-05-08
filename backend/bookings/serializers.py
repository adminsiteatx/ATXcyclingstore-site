from rest_framework import serializers
from .models import Booking
from django.utils.timezone import localtime
from django.utils import timezone


class BookingSerializer(serializers.ModelSerializer):


    data = serializers.DateTimeField(input_formats=["%Y-%m-%dT%H:%M"])


    class Meta:
        model = Booking
        fields = ['id', 'nome', 'email', 'data', 'mensagem']
        read_only_fields = ['id']

    from django.utils import timezone

    def validate_data(self, value):
        # garantir que está em timezone local
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())

        data_local = timezone.localtime(value)

        # 🔒 duplicados
        if Booking.objects.filter(data=value).exists():
            raise serializers.ValidationError(
                "Já existe uma marcação para este horário."
            )

        # ⏰ horário
        if data_local.hour < 9 or data_local.hour > 18:
            raise serializers.ValidationError(
                "Horário fora do período permitido (9h–18h)."
            )

        # ⏱ intervalos
        if data_local.minute != 0:
            raise serializers.ValidationError(
                "As marcações devem ser feitas em horas certas (ex: 10:00, 11:00)."
            )

        return value