from django.contrib import admin
from .models import Booking, CapacidadeSemanal


@admin.register(CapacidadeSemanal)
class CapacidadeSemanalAdmin(admin.ModelAdmin):
    list_display = ("capacidade", "atualizado_em")

    def has_add_permission(self, request):
        # só existe 1 registo
        return not CapacidadeSemanal.objects.exists()


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("numero_pedido", "nome", "email", "data", "estado", "criado_em")
    list_filter = ("estado", "data")
    search_fields = ("nome", "email", "numero_pedido")
    readonly_fields = ("numero_pedido", "token_tracking", "criado_em", "event_id")

    fieldsets = (
        ("Cliente", {
            "fields": ("nome", "email", "mensagem")
        }),
        ("Marcação", {
            "fields": ("data", "numero_pedido", "event_id", "criado_em")
        }),
        ("Tracking", {
            "fields": ("estado", "token_tracking")
        }),
    )
