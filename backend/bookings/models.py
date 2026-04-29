from django.db import models

class Booking(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    data = models.DateTimeField()
    mensagem = models.TextField()
    event_id = models.CharField(max_length=255, blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome