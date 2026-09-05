from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core import signing
import datetime
import os
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .models import Booking, CapacidadeSemanal
from .serializers import BookingSerializer, bookings_na_semana, get_capacidade
from .signals import _resend_send, FRONTEND_URL

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
            calendarId="5db8c4f296ebc5df58acb2195ea703f01106e91a59660d47650ab2ce0c8afb30@group.calendar.google.com",
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

    def perform_create(self, serializer):
        user = None
        try:
            auth = JWTAuthentication()
            result = auth.authenticate(self.request)
            if result:
                user, _ = result
        except Exception:
            pass
        serializer.save(user=user)


# ---------------------------------------------------------------------------
# Dias disponíveis (próximas 8 semanas, terça a sábado)
# ---------------------------------------------------------------------------

class AvailableDaysView(APIView):
    def get(self, request):
        agora = timezone.localtime()
        hoje = agora.date()
        # sábado (weekday 5) fecha às 10h, dias de semana fecham às 15h
        hora_fecho = 10 if hoje.weekday() == 5 else 15
        data_minima = hoje + datetime.timedelta(days=1) if agora.hour >= hora_fecho else hoje
        dias = []

        for i in range(8):
            segunda = hoje - datetime.timedelta(days=hoje.weekday()) + datetime.timedelta(weeks=i)
            sabado  = segunda + datetime.timedelta(days=5)

            capacidade  = get_capacidade(segunda)
            bloqueada   = capacidade == 0
            total_db    = bookings_na_semana(segunda)
            total_cal   = _calendar_eventos_semana(segunda, sabado)
            total       = max(total_db, total_cal)
            disponiveis = max(0, capacidade - total)
            cheia = bloqueada or disponiveis <= 0

            # terça (weekday 1) a sábado (weekday 5)
            for offset in range(1, 6):
                dia = segunda + datetime.timedelta(days=offset)
                if dia < data_minima:
                    continue
                dias.append({
                    "data":        dia.isoformat(),
                    "label":       _label_dia(dia),
                    "entrega":     _entrega(dia),
                    "disponiveis": disponiveis,
                    "capacidade":  capacidade,
                    "cheia":       cheia,
                    "bloqueada":   bloqueada,
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
            "entrega_prevista": _entrega(booking.data),
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
            "entrega_prevista": _entrega(booking.data),
            "criado_em": booking.criado_em.isoformat(),
        })


# ---------------------------------------------------------------------------
# Gestão — listar todas as marcações (protegida por token simples)
# ---------------------------------------------------------------------------

_GESTAO_SESSION_SALT = 'gestao-session'
_GESTAO_SESSION_MAX_AGE = 43200  # 12 horas


def check_gestao_auth(request):
    token = request.headers.get("X-Gestao-Token", "")
    if not token:
        return False
    try:
        signing.loads(token, salt=_GESTAO_SESSION_SALT, max_age=_GESTAO_SESSION_MAX_AGE)
        return True
    except Exception:
        return False


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
            "telefone": b.telefone,
            "data": b.data.isoformat(),
            "estado": b.estado,
            "estado_label": b.get_estado_display(),
            "mensagem": b.mensagem or "",
            "criado_em": b.criado_em.isoformat(),
        } for b in bookings]
        return Response(data)


# ---------------------------------------------------------------------------
# Gestão — atualizar estado de uma marcação
# ---------------------------------------------------------------------------

def _email_html(numero_pedido, tracking_url, nome, titulo, corpo, rodape):
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto;color:#111">
      <h2 style="color:#0077cc">{titulo}</h2>
      <p>Olá <strong>{nome}</strong>,</p>
      <p>{corpo}</p>
      <div style="background:#f4f4f4;border-radius:8px;padding:16px;margin:24px 0">
        <p style="margin:0 0 8px 0"><strong>Nº de pedido:</strong> {numero_pedido}</p>
        <p style="margin:0">{rodape}</p>
      </div>
      <a href="{tracking_url}"
         style="display:inline-block;background:#0077cc;color:white;padding:12px 24px;
                border-radius:6px;text-decoration:none;font-weight:500">
        Acompanhar a minha bicicleta
      </a>
      <p style="margin-top:32px;font-size:13px;color:#888">
        Também podes consultar em
        <a href="{FRONTEND_URL}/pages/tracking.html">{FRONTEND_URL}/pages/tracking.html</a>
        com o número <strong>{numero_pedido}</strong>.
      </p>
      <hr style="margin-top:40px;border:none;border-top:1px solid #eee">
      <p style="font-size:12px;color:#aaa">ATXcyclingstore · +351 918 583 829 · atxcyclingstore@gmail.com</p>
    </div>"""


def _enviar_email_recebida(booking):
    numero_pedido = booking.numero_pedido or f"ATX-{booking.pk}"
    tracking_url  = f"{FRONTEND_URL}/pages/tracking.html?token={booking.token_tracking}"
    _resend_send(
        to=booking.email,
        subject=f"[{numero_pedido}] A sua bicicleta foi recebida — ATXcyclingstore",
        html=_email_html(
            numero_pedido, tracking_url, booking.nome,
            "A sua bicicleta foi recebida",
            "A sua bicicleta foi recebida na nossa oficina e está a aguardar diagnóstico.",
            "Acompanhe o estado em tempo real através do botão abaixo.",
        ),
    )


def _enviar_email_reparacao(booking):
    numero_pedido = booking.numero_pedido or f"ATX-{booking.pk}"
    tracking_url  = f"{FRONTEND_URL}/pages/tracking.html?token={booking.token_tracking}"
    _resend_send(
        to=booking.email,
        subject=f"[{numero_pedido}] A sua bicicleta está em reparação — ATXcyclingstore",
        html=_email_html(
            numero_pedido, tracking_url, booking.nome,
            "A sua bicicleta está em reparação",
            "A sua bicicleta já se encontra em reparação. Assim que estiver pronta iremos notificá-lo.",
            "Acompanhe o estado em tempo real através do botão abaixo.",
        ),
    )


def _enviar_email_pronta(booking):
    numero_pedido = booking.numero_pedido or f"ATX-{booking.pk}"
    tracking_url  = f"{FRONTEND_URL}/pages/tracking.html?token={booking.token_tracking}"
    _resend_send(
        to=booking.email,
        subject=f"[{numero_pedido}] A sua bicicleta está pronta — ATXcyclingstore",
        html=_email_html(
            numero_pedido, tracking_url, booking.nome,
            "A sua bicicleta está pronta",
            "Temos uma ótima notícia: a sua bicicleta já está pronta e pode ser levantada na loja.",
            "Por favor traga este número quando vier levantar a bicicleta.",
        ),
    )


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

        if novo_estado == "recebida":
            _enviar_email_recebida(booking)
        elif novo_estado == "reparacao":
            _enviar_email_reparacao(booking)
        elif novo_estado == "pronta":
            _enviar_email_pronta(booking)

        return Response({
            "id": booking.id,
            "estado": booking.estado,
            "estado_label": booking.get_estado_display(),
        })


# ---------------------------------------------------------------------------
# Cancelar marcação
# ---------------------------------------------------------------------------

class CancelBookingView(APIView):
    def delete(self, request, booking_id):
        if not check_gestao_auth(request):
            return Response({"error": "Não autorizado"}, status=401)
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking não encontrado"}, status=404)
        booking.delete()
        return Response({"message": "Marcação cancelada com sucesso"})


# ---------------------------------------------------------------------------
# Sincronizar Calendar → DB  (apaga no DB o que foi apagado no Calendar)
# ---------------------------------------------------------------------------

class SyncCalendarView(APIView):
    def post(self, request):
        if not check_gestao_auth(request):
            return Response({"error": "Não autorizado"}, status=401)

        try:
            google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
            creds = service_account.Credentials.from_service_account_info(
                google_creds,
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            service = build("calendar", "v3", credentials=creds)
        except Exception as e:
            return Response({"error": f"Erro ao ligar ao Calendar: {e}"}, status=500)

        calendar_id = "5db8c4f296ebc5df58acb2195ea703f01106e91a59660d47650ab2ce0c8afb30@group.calendar.google.com"
        bookings = Booking.objects.exclude(event_id__isnull=True).exclude(event_id="")
        eliminadas = 0

        for booking in bookings:
            try:
                event = service.events().get(
                    calendarId=calendar_id,
                    eventId=booking.event_id
                ).execute()
                if event.get("status") == "cancelled":
                    booking.delete()
                    eliminadas += 1
            except Exception:
                booking.delete()
                eliminadas += 1

        return Response({"sincronizado": True, "eliminadas": eliminadas})


# ---------------------------------------------------------------------------
# Capacidade por semana
# ---------------------------------------------------------------------------

class CapacidadeView(APIView):
    def get(self, request):
        if not check_gestao_auth(request):
            return Response({"error": "Não autorizado"}, status=401)

        semana_str = request.query_params.get("semana")
        if not semana_str:
            return Response({"error": "Parâmetro 'semana' obrigatório (YYYY-MM-DD)"}, status=400)

        try:
            segunda = datetime.date.fromisoformat(semana_str)
        except ValueError:
            return Response({"error": "Formato de data inválido"}, status=400)

        vagas_total = get_capacidade(segunda)
        sabado = segunda + datetime.timedelta(days=5)
        total_db  = bookings_na_semana(segunda)
        total_cal = _calendar_eventos_semana(segunda, sabado)
        vagas_usadas = max(total_db, total_cal)

        return Response({
            "semana": segunda.isoformat(),
            "vagas_total": vagas_total,
            "vagas_usadas": vagas_usadas,
        })

    def post(self, request):
        if not check_gestao_auth(request):
            return Response({"error": "Não autorizado"}, status=401)

        semana_str = request.data.get("semana")
        vagas_total = request.data.get("vagas_total")

        if not semana_str or vagas_total is None:
            return Response({"error": "Campos 'semana' e 'vagas_total' obrigatórios"}, status=400)

        try:
            segunda = datetime.date.fromisoformat(semana_str)
            vagas_total = int(vagas_total)
            if vagas_total < 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({"error": "Dados inválidos"}, status=400)

        obj, _ = CapacidadeSemanal.objects.update_or_create(
            semana=segunda,
            defaults={"vagas_total": vagas_total},
        )

        return Response({
            "semana": obj.semana.isoformat(),
            "vagas_total": obj.vagas_total,
        })
