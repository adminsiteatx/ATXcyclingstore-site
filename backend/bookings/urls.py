from django.urls import path
from .views import BookingCreateView
from .views import AvailableSlotsView

urlpatterns = [
    path('bookings/', BookingCreateView.as_view()),
    path('available-slots/', AvailableSlotsView.as_view()),
]