import logging
from decimal import Decimal

from loja.dominio import NovoPedido, PedidoCriado, PedidoSite
from loja.erros import CheckoutIndisponivel, ItemIndisponivel, PedidoRecusado

from . import mapeamento
from .cliente import ClienteBackoffice
from .erros import BackofficeIndisponivel, BackofficeNaoEncontrado, BackofficeRecusou

logger = logging.getLogger(__name__)

STATUS_DE_ITEM_INDISPONIVEL = (409, 422)


class PedidosBackoffice:
    def __init__(self, cliente: ClienteBackoffice):
        self.cliente = cliente

    def criar(self, pedido: NovoPedido) -> PedidoCriado:
        corpo = {
            "numero_externo": pedido.numero,
            "frete": str(pedido.frete),
            "cliente": pedido.cliente,
            "entrega": pedido.entrega,
            "pagamento": pedido.pagamento,
            "itens": [{"sku": sku, "quantidade": quantidade} for sku, quantidade in pedido.itens],
        }
        try:
            status, dados = self.cliente.post("pedidos/", corpo)
        except BackofficeIndisponivel as erro:
            raise CheckoutIndisponivel(str(erro)) from erro
        except BackofficeRecusou as erro:
            if erro.status in STATUS_DE_ITEM_INDISPONIVEL and erro.dados.get("sku"):
                raise ItemIndisponivel(erro.dados["sku"]) from erro
            raise PedidoRecusado(str(erro)) from erro
        return PedidoCriado(numero=dados["numero_externo"], total=Decimal(dados["total"]), criado=status == 201)

    def obter(self, numero: str) -> PedidoSite | None:
        try:
            return mapeamento.pedido(self.cliente.get(f"pedidos/{numero}/"))
        except BackofficeNaoEncontrado:
            return None

    def do_cliente(self, cliente_id: str) -> list[PedidoSite]:
        dados = self.cliente.get(f"clientes/{cliente_id}/pedidos/")
        return [mapeamento.pedido(p) for p in dados["itens"]]
