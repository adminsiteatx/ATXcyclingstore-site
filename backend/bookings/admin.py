from django.contrib import admin
from .models import Booking

from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path

from .utils import sync_with_calendar
from django import forms
from django.core.exceptions import ValidationError
from django.utils.timezone import localtime

from .utils import is_time_available

class BookingAdminForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = "__all__"

    def clean_data(self):

        data = self.cleaned_data["data"]

        BASE_DIR = Path(__file__).resolve().parent.parent

        creds = service_account.Credentials.from_service_account_file(
            BASE_DIR / "credentials.json",
            scopes=["https://www.googleapis.com/auth/calendar"]
        )

        service = build("calendar", "v3", credentials=creds)

        data_local = localtime(data)

        if not is_time_available(service, data_local):

            raise ValidationError(
                "Já existe uma marcação nesse horário."
            )

        return data

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingAdminForm

    list_display = ("nome", "email", "data")

    def changelist_view(self, request, extra_context=None):

        # print("ADMIN OPENED")

        BASE_DIR = Path(__file__).resolve().parent.parent

        creds = service_account.Credentials.from_service_account_file(
            BASE_DIR / "credentials.json",
            scopes=["https://www.googleapis.com/auth/calendar"]
        )

        service = build("calendar", "v3", credentials=creds)

        sync_with_calendar(service, "adminsiteatx@gmail.com")

        return super().changelist_view(request, extra_context)