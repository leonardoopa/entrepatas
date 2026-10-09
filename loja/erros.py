class CheckoutError(Exception):
    pass


class CarrinhoVazio(CheckoutError):
    pass


class ItemIndisponivel(CheckoutError):
    def __init__(self, sku: str, nome: str = ""):
        super().__init__(f"Item indisponível: {nome or sku}")
        self.sku = sku
        self.nome = nome or sku


class PedidoRecusado(CheckoutError):
    pass


class CheckoutIndisponivel(CheckoutError):
    """O backoffice não respondeu; o pedido pode ser reenviado com o mesmo número."""
