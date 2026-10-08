from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

from loja.texto import normalizar

CENTAVOS = Decimal("0.01")
PARCELA_MINIMA = Decimal("25")
MAX_PARCELAS = 10
NOTA_MAXIMA = 5


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


class Departamento(models.Model):
    nome = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("loja:departamento", args=[self.slug])


class Subdepartamento(models.Model):
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name="subdepartamentos")
    nome = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["departamento__ordem", "ordem", "nome"]
        verbose_name = "subdepartamento"

    def __str__(self):
        return f"{self.departamento} / {self.nome}"


class Produto(models.Model):
    class Tipo(models.TextChoices):
        SACO = "saco", "Saco"
        LATA = "lata", "Lata"
        FRASCO = "frasco", "Frasco"
        BOLA = "bola", "Bola"
        OSSO = "osso", "Osso"
        CAIXA = "caixa", "Caixa"
        CAMA = "cama", "Cama"
        COLEIRA = "coleira", "Coleira"
        POTE = "pote", "Pote"

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="produtos")
    departamento = models.ForeignKey(
        Departamento, on_delete=models.PROTECT, related_name="produtos", null=True, blank=True,
    )
    subdepartamento = models.ForeignKey(
        Subdepartamento, on_delete=models.PROTECT, related_name="produtos", null=True, blank=True,
    )
    nome = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    marca = models.CharField(max_length=80, blank=True)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    preco_promocional = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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
    texto_busca = models.TextField(editable=False, default="")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.texto_busca = normalizar(f"{self.nome} {self.marca} {self.descricao}")
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = {*kwargs["update_fields"], "texto_busca"}
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("loja:produto", args=[self.slug])

    @property
    def preco_final(self) -> Decimal:
        return self.preco_promocional or self.preco

    @property
    def em_promocao(self) -> bool:
        return self.preco_promocional is not None and self.preco_promocional < self.preco

    @property
    def desconto_percentual(self) -> int:
        if not self.em_promocao:
            return 0
        return int((1 - self.preco_promocional / self.preco) * 100)

    @property
    def parcelas(self) -> tuple[int, Decimal]:
        quantidade = max(1, min(MAX_PARCELAS, int(self.preco_final // PARCELA_MINIMA)))
        return quantidade, (self.preco_final / quantidade).quantize(CENTAVOS, ROUND_HALF_UP)

    @property
    def avaliacao_pct(self) -> int:
        return int(self.avaliacao / NOTA_MAXIMA * 100)
