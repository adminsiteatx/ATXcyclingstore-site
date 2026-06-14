from django.db import models
import uuid


class CapacidadeSemanal(models.Model):
    """Configuração da capacidade máxima de bicicletas por semana."""
    capacidade = models.PositiveIntegerField(default=5)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Capacidade Semanal"
        verbose_name_plural = "Capacidade Semanal"

    def __str__(self):
        return f"Capacidade: {self.capacidade} bicicletas/semana"


class Booking(models.Model):
    ESTADO_CHOICES = [
        ('recebida', 'Recebida'),
        ('diagnostico', 'Em Diagnóstico'),
        ('reparacao', 'Em Reparação'),
        ('pronta', 'Pronta'),
        ('entregue', 'Entregue'),
    ]

    nome = models.CharField(max_length=100)
    email = models.EmailField()
    data = models.DateField()  # agora só a data (semana), sem hora fixa
    mensagem = models.TextField(blank=True)
    event_id = models.CharField(max_length=255, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # tracking
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='recebida')
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
