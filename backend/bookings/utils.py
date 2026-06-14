from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from .models import Booking

import os
import json


def create_calendar_event(booking):
    """Cria um evento no Google Calendar para o dia da marcação (09:00–10:00)."""
    google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])

    creds = service_account.Credentials.from_service_account_info(
        google_creds,
        scopes=["https://www.googleapis.com/auth/calendar"]
    )

    service = build("calendar", "v3", credentials=creds)

    data_str = booking.data.isoformat()

    event = {
        "summary": f"Marcação — {booking.nome}",
        "description": booking.mensagem or "",
        "start": {
            "dateTime": f"{data_str}T09:00:00",
            "timeZone": "Europe/Lisbon",
        },
        "end": {
            "dateTime": f"{data_str}T10:00:00",
            "timeZone": "Europe/Lisbon",
        },
    }

    event = service.events().insert(
        calendarId="adminsiteatx@gmail.com",
        body=event
    ).execute()

    booking.event_id = event["id"]
    booking.save(update_fields=["event_id"])


def sync_with_calendar(service, calendar_id):
    """Remove do DB marcações cujo evento foi apagado manualmente no Calendar."""
    bookings = Booking.objects.exclude(event_id__isnull=True).exclude(event_id="")

    for booking in bookings:
        try:
            event = service.events().get(
                calendarId=calendar_id,
                eventId=booking.event_id
            ).execute()

            if event.get("status") == "cancelled":
                booking.delete()

        except Exception as e:
            print("EVENTO APAGADO:", booking.event_id, e)
            booking.delete()
