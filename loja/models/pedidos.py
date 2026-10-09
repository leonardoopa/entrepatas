from decimal import Decimal

from django.conf import settings
from django.db import models

from .catalogo import Produto


class Pedido(models.Model):
    class Status(models.TextChoices):
        NOVO = "novo", "Novo"
        PAGO = "pago", "Pago"
        ENVIADO = "enviado", "Enviado"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos",
    )
    nome = models.CharField(max_length=120)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    cep = models.CharField(max_length=9)
    endereco = models.CharField(max_length=200)
    cidade = models.CharField(max_length=80)
    uf = models.CharField(max_length=2)
    frete = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NOVO)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido #{self.pk} - {self.nome}"

    @property
    def subtotal(self) -> Decimal:
        return sum((item.subtotal for item in self.itens.all()), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.frete


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto}"

    @property
    def subtotal(self) -> Decimal:
        return self.preco_unitario * self.quantidade
