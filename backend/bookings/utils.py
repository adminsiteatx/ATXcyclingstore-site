from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import localtime


from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta
from pathlib import Path
from .models import Booking



def send_email(to_email, subject, message):
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
    )



def create_calendar_event(booking):
    BASE_DIR = Path(__file__).resolve().parent.parent

    creds = service_account.Credentials.from_service_account_file(
        BASE_DIR / "credentials.json",
        scopes=["https://www.googleapis.com/auth/calendar"]
    )

    service = build("calendar", "v3", credentials=creds)

    start = localtime(booking.data)

    # 🔒 verificar disponibilidade
    if not is_time_available(service, start):
        raise Exception("Horário já ocupado no calendário.")

    end = start + timedelta(hours=1)

    event = {
        "summary": f"Marcação - {booking.nome}",
        "description": booking.mensagem,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "Europe/Lisbon",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "Europe/Lisbon",
        },
    }

    event = service.events().insert(
        calendarId="adminsiteatx@gmail.com",
        body=event
    ).execute()

    booking.event_id = event["id"]
    booking.save()


def is_time_available(service, start_time):
    end_time = start_time + timedelta(hours=1)

    events_result = service.events().list(
        calendarId="adminsiteatx@gmail.com",
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True
    ).execute()

    events = events_result.get('items', [])

    return len(events) == 0

def sync_with_calendar(service, calendar_id):
    bookings = Booking.objects.exclude(event_id=None)

    for booking in bookings:
        try:
            service.events().get(
                calendarId=calendar_id,
                eventId=booking.event_id
            ).execute()
        except:
            # evento não existe → apagar da BD
            booking.delete()