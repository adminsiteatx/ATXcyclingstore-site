from django.db import models
from django.contrib.auth.models import User
import uuid


class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente')
    telefone = models.CharField(max_length=20)
    aceita_sms = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"


class CapacidadeSemanal(models.Model):
    """Capacidade máxima de marcações por semana (identificada pela segunda-feira)."""
    semana = models.DateField(unique=True)
    vagas_total = models.PositiveIntegerField(default=10)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Capacidade Semanal"
        verbose_name_plural = "Capacidades Semanais"
        ordering = ['semana']

    def __str__(self):
        return f"Semana {self.semana.isoformat()}: {self.vagas_total} vagas"


class Booking(models.Model):
    ESTADO_CHOICES = [
        ('marcada', 'Marcação Efetuada'),
        ('recebida', 'Recebida'),
        ('diagnostico', 'Em Diagnóstico'),
        ('reparacao', 'Em Reparação'),
        ('pronta', 'Pronta'),
        ('entregue', 'Entregue'),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='bookings')
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    data = models.DateField()
    mensagem = models.TextField(blank=True)
    event_id = models.CharField(max_length=255, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # tracking
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='marcada')
    token_tracking = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    numero_pedido = models.CharField(max_length=20, blank=True)  # ex: ATX-2025-0042

    def save(self, *args, **kwargs):
        # gerar número de pedido legível na primeira gravação
        if not self.numero_pedido:
            super().save(*args, **kwargs)
            self.numero_pedido = f"ATX-{self.criado_em.year}-{self.pk:04d}"
            kwargs['update_fields'] = ['numero_pedido'] if kwargs.get('update_fields') else None
            super().save(update_fields=['numero_pedido'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_pedido} — {self.nome}"
