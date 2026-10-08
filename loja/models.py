from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

CENTAVOS = Decimal("0.01")
PARCELA_MINIMA = Decimal("25")
MAX_PARCELAS = 10


class Categoria(models.Model):
    """Animal (cães, gatos, ...)."""

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


class Departamento(models.Model):
    """Tipo de produto (rações, brinquedos, higiene, ...)."""

    nome = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("loja:departamento", args=[self.slug])


class Produto(models.Model):
    class Tipo(models.TextChoices):
        """Formato da arte exibida quando o produto não tem foto."""

        SACO = "saco", "Saco"
        LATA = "lata", "Lata"
        FRASCO = "frasco", "Frasco"
        BOLA = "bola", "Bola"
        OSSO = "osso", "Osso"
        CAIXA = "caixa", "Caixa"
        CAMA = "cama", "Cama"
        COLEIRA = "coleira", "Coleira"
        POTE = "pote", "Pote"

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="produtos"
    )
    departamento = models.ForeignKey(
        Departamento, on_delete=models.PROTECT, related_name="produtos",
        null=True, blank=True,
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
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.CAIXA)
    cor = models.CharField(
        "cor da arte", max_length=7, default="#17375e",
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use o formato #RRGGBB.")],
        help_text="Cor hexadecimal usada na arte sem foto, ex.: #F2B544.",
    )
    avaliacao = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    num_avaliacoes = models.PositiveIntegerField(default=0)
    vendas = models.PositiveIntegerField(default=0)
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

    @property
    def parcelas(self):
        """(quantidade, valor) do parcelamento sem juros."""
        n = max(1, min(MAX_PARCELAS, int(self.preco_final // PARCELA_MINIMA)))
        return n, (self.preco_final / n).quantize(CENTAVOS, ROUND_HALF_UP)

    @property
    def avaliacao_pct(self):
        """Preenchimento das estrelas, 0-100."""
        return int(self.avaliacao / 5 * 100)


class Pedido(models.Model):
    class Status(models.TextChoices):
        NOVO = "novo", "Novo"
        PAGO = "pago", "Pago"
        ENVIADO = "enviado", "Enviado"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pedidos",
    )
    nome = models.CharField(max_length=120)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    cep = models.CharField(max_length=9)
    endereco = models.CharField(max_length=200)
    cidade = models.CharField(max_length=80)
    uf = models.CharField(max_length=2)
    frete = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NOVO
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido #{self.pk} - {self.nome}"

    @property
    def subtotal(self):
        return sum((i.subtotal for i in self.itens.all()), Decimal("0"))

    @property
    def total(self):
        return self.subtotal + self.frete


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
