# bookings/signals.py

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from .models import Booking
from .utils import create_calendar_event

from google.oauth2 import service_account
from googleapiclient.discovery import build

import os
import json
import resend

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://atxcyclingstore.vercel.app")
DONO_EMAIL   = os.environ.get("DONO_EMAIL", "adminsiteatx@gmail.com")
FROM_EMAIL   = os.environ.get("FROM_EMAIL", "ATXcyclingstore <onboarding@resend.dev>")


def _resend_send(to: str, subject: str, html: str):
    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    if not resend.api_key:
        print("RESEND_API_KEY não configurada — email não enviado.")
        return
    try:
        resp = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        print("Resend OK:", resp)
    except Exception as e:
        print("ERRO Resend:", e)


@receiver(post_save, sender=Booking)
def booking_created(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        create_calendar_event(instance)
    except Exception as e:
        print("ERRO CALENDAR:", e)

    tracking_url  = f"{FRONTEND_URL}/pages/tracking.html?token={instance.token_tracking}"
    numero_pedido = instance.numero_pedido or f"ATX-{instance.pk}"
    data_fmt      = instance.data.strftime("%d/%m/%Y")

    # ── email ao cliente ──────────────────────────────────────────────────
    _resend_send(
        to=instance.email,
        subject=f"[{numero_pedido}] Marcação confirmada — ATXcyclingstore",
        html=f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto;color:#111">
          <h2 style="color:#0077cc">Marcação confirmada — ATXcyclingstore</h2>
          <p>Olá <strong>{instance.nome}</strong>,</p>
          <p>A tua bicicleta foi registada na nossa oficina.
             Podes acompanhar o estado em tempo real através do link abaixo.</p>
          <div style="background:#f4f4f4;border-radius:8px;padding:16px;margin:24px 0">
            <p style="margin:0 0 8px 0"><strong>Nº de pedido:</strong> {numero_pedido}</p>
            <p style="margin:0"><strong>Semana prevista:</strong> {data_fmt}</p>
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
        </div>""",
    )

    # ── email ao dono ─────────────────────────────────────────────────────
    _resend_send(
        to=DONO_EMAIL,
        subject=f"Nova marcação: {numero_pedido} — {instance.nome}",
        html=f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto;color:#111">
          <h3>Nova marcação recebida</h3>
          <p><strong>Pedido:</strong> {numero_pedido}</p>
          <p><strong>Cliente:</strong> {instance.nome} ({instance.email})</p>
          <p><strong>Semana:</strong> {data_fmt}</p>
          <p><strong>Mensagem:</strong> {instance.mensagem or '—'}</p>
        </div>""",
    )


@receiver(post_delete, sender=Booking)
def booking_deleted(sender, instance, **kwargs):
    if not instance.event_id:
        return

    try:
        google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(
            google_creds,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(
            calendarId="adminsiteatx@gmail.com",
            eventId=instance.event_id
        ).execute()
        print("Evento apagado do calendar")
    except Exception as e:
        print("Erro ao apagar evento:", e)
