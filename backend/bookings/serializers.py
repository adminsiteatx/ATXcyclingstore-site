from rest_framework import serializers
from .models import Booking, CapacidadeSemanal
from django.utils import timezone
import datetime


VAGAS_PADRAO = 10

def get_capacidade(segunda: datetime.date) -> int:
    try:
        return CapacidadeSemanal.objects.get(semana=segunda).vagas_total
    except CapacidadeSemanal.DoesNotExist:
        return VAGAS_PADRAO


def bookings_na_semana(data: datetime.date) -> int:
    """Conta marcações existentes na mesma semana ISO (segunda→domingo)."""
    # início da semana (segunda-feira)
    inicio_semana = data - datetime.timedelta(days=data.weekday())
    fim_semana = inicio_semana + datetime.timedelta(days=6)
    return Booking.objects.filter(data__range=[inicio_semana, fim_semana]).count()


class BookingSerializer(serializers.ModelSerializer):
    data = serializers.DateField(input_formats=["%Y-%m-%d"])

    class Meta:
        model = Booking
        fields = ['id', 'nome', 'email', 'telefone', 'data', 'mensagem',
                  'estado', 'token_tracking', 'numero_pedido']
        read_only_fields = ['id', 'estado', 'token_tracking', 'numero_pedido']

    def validate_data(self, value):
        hoje = timezone.localdate()

        # não aceitar datas passadas
        if value < hoje:
            raise serializers.ValidationError("Não é possível marcar para uma data passada.")

        # sem domingos nem segundas
        if value.weekday() in (0, 6):  # 0=segunda, 6=domingo
            raise serializers.ValidationError(
                "Não fazemos marcações à segunda-feira nem ao domingo."
            )

        # verificar capacidade da semana
        segunda = value - datetime.timedelta(days=value.weekday())
        capacidade = get_capacidade(segunda)
        total = bookings_na_semana(value)

        if total >= capacidade:
            raise serializers.ValidationError(
                f"Sem disponibilidade para esta semana."
            )

        return value
