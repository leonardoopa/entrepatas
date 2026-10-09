from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.urls import reverse

CENTAVOS = Decimal("0.01")
PARCELA_MINIMA = Decimal("25")
MAX_PARCELAS = 10
NOTA_MAXIMA = 5

ROTULOS_STATUS_PEDIDO = {
    "novo": "Novo", "pago": "Pago", "enviado": "Enviado", "entregue": "Entregue", "cancelado": "Cancelado",
}


@dataclass(frozen=True)
class AnimalRef:
    slug: str
    nome: str
    emoji: str = ""

    def get_absolute_url(self) -> str:
        return reverse("loja:categoria", args=[self.slug])


@dataclass(frozen=True)
class DepartamentoRef:
    slug: str
    nome: str

    def get_absolute_url(self) -> str:
        return reverse("loja:departamento", args=[self.slug])


@dataclass(frozen=True)
class SubdepartamentoRef:
    slug: str
    nome: str
    departamento: str = ""


@dataclass(frozen=True)
class MarcaRef:
    slug: str
    nome: str


@dataclass(frozen=True)
class Variacao:
    sku: str
    slug: str
    rotulo: str
    preco_final: Decimal
    estoque: int

    def get_absolute_url(self) -> str:
        return reverse("loja:produto", args=[self.slug])


@dataclass(frozen=True)
class ProdutoCatalogo:
    sku: str
    slug: str
    nome: str
    descricao: str
    marca: str
    marca_slug: str
    categoria: AnimalRef
    departamento: DepartamentoRef | None
    subdepartamento: SubdepartamentoRef | None
    grupo: str
    variacao: str
    preco: Decimal
    preco_promocional: Decimal | None
    preco_final: Decimal
    estoque: int
    avaliacao: Decimal
    num_avaliacoes: int
    tipo: str
    cor: str
    imagens: tuple[str, ...] = ()
    promocao_fim: datetime | None = None
    variacoes: tuple[Variacao, ...] = ()

    def get_absolute_url(self) -> str:
        return reverse("loja:produto", args=[self.slug])

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


@dataclass(frozen=True)
class Pagina(Sequence):
    itens: tuple[ProdutoCatalogo, ...]
    numero: int
    total_paginas: int
    total: int

    def __iter__(self) -> Iterator[ProdutoCatalogo]:
        return iter(self.itens)

    def __len__(self) -> int:
        return len(self.itens)

    def __getitem__(self, indice):
        return self.itens[indice]

    @property
    def tem_anterior(self) -> bool:
        return self.numero > 1

    @property
    def tem_proxima(self) -> bool:
        return self.numero < self.total_paginas

    @property
    def intervalo(self) -> range:
        return range(1, self.total_paginas + 1)


@dataclass(frozen=True)
class Facetas:
    animais: tuple[AnimalRef, ...] = ()
    departamentos: tuple[DepartamentoRef, ...] = ()
    subdepartamentos: tuple[SubdepartamentoRef, ...] = ()
    marcas: tuple[MarcaRef, ...] = ()


@dataclass(frozen=True)
class ResultadoListagem:
    pagina: Pagina
    facetas: Facetas


@dataclass(frozen=True)
class EntradaMenu:
    departamento: DepartamentoRef
    subdepartamentos: tuple[SubdepartamentoRef, ...] = ()


@dataclass(frozen=True)
class ItemMenu:
    categoria: AnimalRef
    departamentos: tuple[EntradaMenu, ...] = ()


@dataclass(frozen=True)
class Vitrine:
    codigo: str
    nome: str
    itens: tuple[ProdutoCatalogo, ...] = ()


@dataclass(frozen=True)
class ItemPedidoSite:
    sku: str
    descricao: str
    quantidade: int
    preco_unitario: Decimal

    @property
    def subtotal(self) -> Decimal:
        return self.preco_unitario * self.quantidade


@dataclass(frozen=True)
class PedidoSite:
    numero: str
    status: str
    subtotal: Decimal
    frete: Decimal
    total: Decimal
    comprado_em: datetime
    itens: tuple[ItemPedidoSite, ...] = ()
    cliente_id: str = ""
    nome: str = ""
    email: str = ""
    entrega: dict = field(default_factory=dict)

    @property
    def status_rotulo(self) -> str:
        return ROTULOS_STATUS_PEDIDO.get(self.status, self.status)

    @property
    def endereco(self) -> str:
        return self.entrega.get("endereco", "")

    @property
    def cidade(self) -> str:
        return self.entrega.get("cidade", "")

    @property
    def uf(self) -> str:
        return self.entrega.get("uf", "")

    @property
    def cep(self) -> str:
        return self.entrega.get("cep", "")


@dataclass(frozen=True)
class NovoPedido:
    numero: str
    itens: tuple[tuple[str, int], ...]
    cliente: dict
    entrega: dict
    frete: Decimal
    pagamento: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PedidoCriado:
    numero: str
    total: Decimal
    criado: bool
