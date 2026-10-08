from decimal import Decimal

from django.db import models
from django.urls import reverse


class Categoria(models.Model):
    nome = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=8, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("loja:categoria", args=[self.slug])


class Produto(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="produtos"
    )
    nome = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    marca = models.CharField(max_length=80, blank=True)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    preco_promocional = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    estoque = models.PositiveIntegerField(default=0)
    imagem = models.ImageField(upload_to="produtos/", blank=True)
    destaque = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("loja:produto", args=[self.slug])

    @property
    def preco_final(self):
        return self.preco_promocional or self.preco

    @property
    def em_promocao(self):
        return self.preco_promocional is not None and self.preco_promocional < self.preco

    @property
    def desconto_percentual(self):
        if not self.em_promocao:
            return 0
        return int((1 - self.preco_promocional / self.preco) * 100)


class Pedido(models.Model):
    class Status(models.TextChoices):
        NOVO = "novo", "Novo"
        PAGO = "pago", "Pago"
        ENVIADO = "enviado", "Enviado"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    nome = models.CharField(max_length=120)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    cep = models.CharField(max_length=9)
    endereco = models.CharField(max_length=200)
    cidade = models.CharField(max_length=80)
    uf = models.CharField(max_length=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NOVO
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido #{self.pk} - {self.nome}"

    @property
    def total(self):
        return sum((i.subtotal for i in self.itens.all()), Decimal("0"))


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    # Preço congelado no momento da compra.
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto}"

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
