from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
import datetime

from .models import Booking, CapacidadeSemanal
from .serializers import BookingSerializer, bookings_na_semana, get_capacidade


# ---------------------------------------------------------------------------
# Criar marcação
# ---------------------------------------------------------------------------

class BookingCreateView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


# ---------------------------------------------------------------------------
# Semanas disponíveis (próximas 8 semanas)
# ---------------------------------------------------------------------------

class AvailableWeeksView(APIView):
    def get(self, request):
        hoje = timezone.localdate()
        capacidade = get_capacidade()
        semanas = []

        for i in range(8):
            # próximas 8 semanas a partir da semana atual
            inicio = hoje - datetime.timedelta(days=hoje.weekday()) + datetime.timedelta(weeks=i)
            fim = inicio + datetime.timedelta(days=4)  # sexta-feira

            # não mostrar semanas que já terminaram
            if fim < hoje:
                continue

            total = bookings_na_semana(inicio)
            disponiveis = capacidade - total

            semanas.append({
                "semana_inicio": inicio.isoformat(),  # segunda
                "semana_fim": fim.isoformat(),  # sexta
                "disponiveis": max(0, disponiveis),
                "capacidade": capacidade,
                "cheia": disponiveis <= 0,
            })

        return Response(semanas)


# ---------------------------------------------------------------------------
# Tracking por token UUID (link no email)
# ---------------------------------------------------------------------------

class TrackingByTokenView(APIView):
    def get(self, request, token):
        booking = get_object_or_404(Booking, token_tracking=token)
        return Response({
            "numero_pedido": booking.numero_pedido,
            "nome": booking.nome,
            "estado": booking.estado,
            "estado_label": booking.get_estado_display(),
            "data": booking.data.isoformat(),
            "criado_em": booking.criado_em.isoformat(),
        })


# ---------------------------------------------------------------------------
# Tracking por número de pedido (página pública)
# ---------------------------------------------------------------------------

class TrackingByNumeroView(APIView):
    def get(self, request, numero):
        booking = get_object_or_404(Booking, numero_pedido=numero.upper())
        return Response({
            "numero_pedido": booking.numero_pedido,
            "nome": booking.nome,
            "estado": booking.estado,
            "estado_label": booking.get_estado_display(),
            "data": booking.data.isoformat(),
            "criado_em": booking.criado_em.isoformat(),
        })


# ---------------------------------------------------------------------------
# Gestão — listar todas as marcações (protegida por token simples)
# ---------------------------------------------------------------------------

GESTAO_TOKEN = "atx-gestao-2025"  # mover para .env em produção


def check_gestao_auth(request):
    token = request.headers.get("X-Gestao-Token", "")
    return token == GESTAO_TOKEN


class GestaoListView(APIView):
    def get(self, request):
        if not check_gestao_auth(request):
            return Response({"error": "Não autorizado"}, status=401)

        bookings = Booking.objects.all().order_by("-criado_em")
        data = [{
            "id": b.id,
            "numero_pedido": b.numero_pedido,
            "nome": b.nome,
            "email": b.email,
            "data": b.data.isoformat(),
            "estado": b.estado,
            "estado_label": b.get_estado_display(),
            "criado_em": b.criado_em.isoformat(),
        } for b in bookings]
        return Response(data)


# ---------------------------------------------------------------------------
# Gestão — atualizar estado de uma marcação
# ---------------------------------------------------------------------------

class GestaoUpdateEstadoView(APIView):
    def patch(self, request, booking_id):
        if not check_gestao_auth(request):
            return Response({"error": "Não autorizado"}, status=401)

        booking = get_object_or_404(Booking, id=booking_id)

        novo_estado = request.data.get("estado")
        estados_validos = [e[0] for e in Booking.ESTADO_CHOICES]

        if novo_estado not in estados_validos:
            return Response({"error": f"Estado inválido. Opções: {estados_validos}"}, status=400)

        booking.estado = novo_estado
        booking.save(update_fields=["estado"])

        return Response({
            "id": booking.id,
            "estado": booking.estado,
            "estado_label": booking.get_estado_display(),
        })


# ---------------------------------------------------------------------------
# Cancelar marcação (mantido do original)
# ---------------------------------------------------------------------------

class CancelBookingView(APIView):
    def get(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking não encontrado"}, status=404)

        booking.delete()
        return Response({"message": "Marcação cancelada com sucesso"})
