from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    BookingCreateView,
    AvailableDaysView,
    TrackingByTokenView,
    TrackingByNumeroView,
    GestaoListView,
    GestaoUpdateEstadoView,
    CancelBookingView,
    SyncCalendarView,
    CapacidadeView,
)
from .auth_views import (
    RegisterView,
    LoginView,
    MeView,
    MinhasMarcacoesView,
    DeleteAccountView,
    SmsBroadcastView,
    UpdateProfileView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    MinhaCancelarMarcacaoView,
)

urlpatterns = [
    # auth
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('auth/me/', MeView.as_view()),
    path('auth/delete-account/', DeleteAccountView.as_view()),
    path('auth/update-profile/', UpdateProfileView.as_view()),
    path('auth/change-password/', ChangePasswordView.as_view()),
    path('auth/password-reset/', PasswordResetRequestView.as_view()),
    path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view()),

    # área pessoal
    path('minha-area/marcacoes/', MinhasMarcacoesView.as_view()),
    path('minha-area/marcacoes/<int:booking_id>/cancelar/', MinhaCancelarMarcacaoView.as_view()),

    # marcações
    path('bookings/', BookingCreateView.as_view()),
    path('cancel/<int:booking_id>/', CancelBookingView.as_view()),

    # disponibilidade por dia
    path('available-days/', AvailableDaysView.as_view()),

    # tracking cliente
    path('tracking/token/<uuid:token>/', TrackingByTokenView.as_view()),
    path('tracking/<str:numero>/', TrackingByNumeroView.as_view()),

    # gestão interna
    path('gestao/bookings/', GestaoListView.as_view()),
    path('gestao/bookings/<int:booking_id>/estado/', GestaoUpdateEstadoView.as_view()),
    path('gestao/bookings/<int:booking_id>/delete/', CancelBookingView.as_view()),
    path('gestao/sync-calendar/', SyncCalendarView.as_view()),
    path('gestao/capacidade/', CapacidadeView.as_view()),
    path('gestao/sms-broadcast/', SmsBroadcastView.as_view()),
]
