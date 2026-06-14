from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
import datetime
import os
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .models import Booking, CapacidadeSemanal
from .serializers import BookingSerializer, bookings_na_semana, get_capacidade

DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _label_dia(d: datetime.date) -> str:
    return f"{DIAS_PT[d.weekday()]}, {d.day} {MESES_PT[d.month - 1]}"


def _entrega(d: datetime.date) -> str:
    """Calcula o texto de entrega prevista conforme o dia de entrada."""
    # terça (1) ou quarta (2) → sábado dessa semana
    if d.weekday() in (1, 2):
        sabado = d + datetime.timedelta(days=(5 - d.weekday()))
        return f"Sábado, {sabado.day} {MESES_PT[sabado.month - 1]}"
    # quinta (3), sexta (4) ou sábado (5) → semana seguinte seg→sáb
    segunda_seguinte = d + datetime.timedelta(days=(7 - d.weekday()))
    sabado_seguinte  = segunda_seguinte + datetime.timedelta(days=5)
    return (
        f"Semana de {segunda_seguinte.day} a "
        f"{sabado_seguinte.day} {MESES_PT[sabado_seguinte.month - 1]}"
    )


def _calendar_eventos_semana(inicio: datetime.date, fim: datetime.date) -> int:
    """Conta eventos no Google Calendar entre inicio e fim (inclusive)."""
    try:
        google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(
            google_creds,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=creds)
        result = service.events().list(
            calendarId="adminsiteatx@gmail.com",
            timeMin=f"{inicio.isoformat()}T00:00:00+01:00",
            timeMax=f"{(fim + datetime.timedelta(days=1)).isoformat()}T00:00:00+01:00",
            singleEvents=True,
        ).execute()
        return len(result.get("items", []))
    except Exception as e:
        print("ERRO Calendar count:", e)
        return 0


# ---------------------------------------------------------------------------
# Criar marcação
# ---------------------------------------------------------------------------

class BookingCreateView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


# ---------------------------------------------------------------------------
# Dias disponíveis (próximas 8 semanas, terça a sábado)
# ---------------------------------------------------------------------------

class AvailableDaysView(APIView):
    def get(self, request):
        hoje = timezone.localdate()
        capacidade = get_capacidade()
        dias = []

        for i in range(8):
            segunda = hoje - datetime.timedelta(days=hoje.weekday()) + datetime.timedelta(weeks=i)
            sabado  = segunda + datetime.timedelta(days=5)

            total_db  = bookings_na_semana(segunda)
            total_cal = _calendar_eventos_semana(segunda, sabado)
            total     = max(total_db, total_cal)
            disponiveis = max(0, capacidade - total)
            cheia = disponiveis <= 0

            # terça (weekday 1) a sábado (weekday 5)
            for offset in range(1, 6):
                dia = segunda + datetime.timedelta(days=offset)
                if dia < hoje:
                    continue
                dias.append({
                    "data":        dia.isoformat(),
                    "label":       _label_dia(dia),
                    "entrega":     _entrega(dia),
                    "disponiveis": disponiveis,
                    "capacidade":  capacidade,
                    "cheia":       cheia,
                })

        return Response(dias)


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
