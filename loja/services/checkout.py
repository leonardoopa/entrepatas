import logging
from collections.abc import Mapping
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from loja.models import ItemPedido, Pedido, Produto

from .carrinho import LinhaCarrinho
from .frete import PoliticaFrete, politica_frete_padrao
from .resumo import montar_resumo

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    pass


class CarrinhoVazio(CheckoutError):
    pass


class ItemIndisponivel(CheckoutError):
    def __init__(self, nome: str):
        super().__init__(f"Item indisponível: {nome}")
        self.nome = nome


def finalizar_pedido(
    *,
    dados_entrega: Mapping[str, Any],
    itens: Mapping[int, int],
    usuario: AbstractBaseUser | None = None,
    politica_frete: PoliticaFrete | None = None,
) -> Pedido:
    if not itens:
        raise CarrinhoVazio()
    politica = politica_frete or politica_frete_padrao()

    try:
        with transaction.atomic():
            produtos = _travar_produtos(itens)
            linhas = [LinhaCarrinho(produtos[pk], quantidade) for pk, quantidade in itens.items()]
            resumo = montar_resumo(linhas, politica)
            pedido = Pedido.objects.create(usuario=usuario, frete=resumo.frete, **dados_entrega)
            _registrar_itens(pedido, linhas)
            _baixar_estoque(linhas)
    except ItemIndisponivel as erro:
        logger.warning("checkout_item_indisponivel item=%s", erro.nome)
        raise

    logger.info(
        "pedido_criado pedido=%s usuario=%s itens=%d total=%s",
        pedido.pk, usuario.pk if usuario else "anonimo", len(linhas), resumo.total,
    )
    return pedido


def _travar_produtos(itens: Mapping[int, int]) -> dict[int, Produto]:
    produtos = {p.pk: p for p in Produto.objects.select_for_update().filter(pk__in=itens)}
    for pk, quantidade in itens.items():
        produto = produtos.get(pk)
        if produto is None or not produto.ativo or produto.estoque < quantidade:
            raise ItemIndisponivel(produto.nome if produto else f"#{pk}")
    return produtos


def _registrar_itens(pedido: Pedido, linhas: list[LinhaCarrinho]) -> None:
    ItemPedido.objects.bulk_create(
        ItemPedido(
            pedido=pedido, produto=linha.produto, quantidade=linha.quantidade,
            preco_unitario=linha.produto.preco_final,
        )
        for linha in linhas
    )


def _baixar_estoque(linhas: list[LinhaCarrinho]) -> None:
    for linha in linhas:
        linha.produto.estoque -= linha.quantidade
        linha.produto.vendas += linha.quantidade
    Produto.objects.bulk_update([linha.produto for linha in linhas], ["estoque", "vendas"])
