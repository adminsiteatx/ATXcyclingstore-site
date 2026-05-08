from rest_framework import generics
from .models import Booking
from .serializers import BookingSerializer
from .utils import send_email, create_calendar_event, sync_with_calendar
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path

class BookingCreateView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


class AvailableSlotsView(APIView):
    def get(self, request):
        date_str = request.GET.get("date")

        if not date_str:
            return Response({"error": "Missing date"}, status=400)

        date = datetime.strptime(date_str, "%Y-%m-%d")

        BASE_DIR = Path(__file__).resolve().parent.parent

        creds = service_account.Credentials.from_service_account_file(
            BASE_DIR / "credentials.json",
            scopes=["https://www.googleapis.com/auth/calendar"]
        )

        service = build("calendar", "v3", credentials=creds)
        sync_with_calendar(service, "adminsiteatx@gmail.com")

        available_slots = []


        for hour in range(9, 19):
            start = make_aware(datetime(
                date.year, date.month, date.day, hour, 0
            ))
            end = start + timedelta(hours=1)

            events = service.events().list(
                calendarId="adminsiteatx@gmail.com",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True
            ).execute().get("items", [])

            if len(events) == 0:
                available_slots.append(f"{hour:02d}:00")

        return Response(available_slots)


class CancelBookingView(APIView):
    def get(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking não encontrado"}, status=404)

        # apagar evento do calendar
        if booking.event_id:
            BASE_DIR = Path(__file__).resolve().parent.parent

            creds = service_account.Credentials.from_service_account_file(
                BASE_DIR / "credentials.json",
                scopes=["https://www.googleapis.com/auth/calendar"]
            )

            service = build("calendar", "v3", credentials=creds)

            service.events().delete(
                calendarId="adminsiteatx@gmail.com",
                eventId=booking.event_id
            ).execute()

        booking.delete()

        return Response({"message": "Marcação cancelada com sucesso"})