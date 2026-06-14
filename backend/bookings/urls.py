from django.urls import path
from .views import (
    BookingCreateView,
    AvailableWeeksView,
    TrackingByTokenView,
    TrackingByNumeroView,
    GestaoListView,
    GestaoUpdateEstadoView,
    CancelBookingView,
)

urlpatterns = [
    # marcações
    path('bookings/', BookingCreateView.as_view()),
    path('cancel/<int:booking_id>/', CancelBookingView.as_view()),

    # disponibilidade semanal
    path('available-weeks/', AvailableWeeksView.as_view()),

    # tracking cliente
    path('tracking/token/<uuid:token>/', TrackingByTokenView.as_view()),
    path('tracking/<str:numero>/', TrackingByNumeroView.as_view()),

    # gestão interna
    path('gestao/bookings/', GestaoListView.as_view()),
    path('gestao/bookings/<int:booking_id>/estado/', GestaoUpdateEstadoView.as_view()),
]
