# bookings/signals.py

from django.dispatch import receiver
from .models import Booking
from .utils import send_email, create_calendar_event
from django.db.models.signals import post_save, post_delete
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json


@receiver(post_save, sender=Booking)
def booking_created(sender, instance, created, **kwargs):
    if created:
        # criar evento calendar
        try:
            create_calendar_event(instance)

        except Exception as e:
            print("ERRO CALENDAR:", e)

        # enviar email
        message = f"""
        Olá {instance.nome},

        A tua marcação foi confirmada.
        """

        send_email(
            instance.email,
            "Confirmação de marcação",
            message
        )

        print("SIGNAL DISPARADO")


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
