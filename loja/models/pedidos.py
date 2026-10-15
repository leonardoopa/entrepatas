from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

ROTULOS_STATUS_PEDIDO = {
    "novo": "Novo", "pago": "Pago", "enviado": "Enviado", "entregue": "Entregue", "cancelado": "Cancelado",
}


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
