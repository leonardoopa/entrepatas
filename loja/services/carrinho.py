import logging
from collections.abc import MutableMapping
from dataclasses import dataclass
from decimal import Decimal

from loja.dominio import ProdutoCatalogo
from loja.portas import CatalogoRepositorio

logger = logging.getLogger(__name__)

SESSION_KEY = "carrinho"


class ProdutoSemEstoque(Exception):
    def __init__(self, produto: ProdutoCatalogo):
        super().__init__(f"Produto sem estoque: {produto.sku}")
        self.produto = produto


@dataclass(frozen=True)
class LinhaCarrinho:
    produto: ProdutoCatalogo
    quantidade: int

    @property
    def subtotal(self) -> Decimal:
        return self.produto.preco_final * self.quantidade


class Carrinho:
    """Carrinho guardado na sessão como {sku: quantidade}. Os produtos vêm do catálogo na hora de exibir."""

    def __init__(self, sessao: MutableMapping, catalogo: CatalogoRepositorio | None = None):
        self._sessao = sessao
        self._catalogo = catalogo

    @property
    def itens(self) -> dict[str, int]:
        return dict(self._sessao.get(SESSION_KEY, {}))

    def __len__(self) -> int:
        return sum(self.itens.values())

    def adicionar(self, produto: ProdutoCatalogo, quantidade: int = 1) -> None:
        if produto.estoque <= 0:
            logger.warning("carrinho_produto_sem_estoque sku=%s", produto.sku)
            raise ProdutoSemEstoque(produto)
        self.definir(produto, self.itens.get(produto.sku, 0) + quantidade)

    def definir(self, produto: ProdutoCatalogo, quantidade: int) -> None:
        itens = self.itens
        quantidade = min(quantidade, produto.estoque)
        if quantidade > 0:
            itens[produto.sku] = quantidade
        else:
            itens.pop(produto.sku, None)
        self._sessao[SESSION_KEY] = itens
        logger.debug("carrinho_item_definido sku=%s quantidade=%s", produto.sku, max(quantidade, 0))

    def remover(self, sku: str) -> None:
        itens = self.itens
        itens.pop(sku, None)
        self._sessao[SESSION_KEY] = itens
        logger.debug("carrinho_item_removido sku=%s", sku)

    def limpar(self) -> None:
        self._sessao.pop(SESSION_KEY, None)

    def linhas(self) -> list[LinhaCarrinho]:
        itens = self.itens
        produtos = {p.sku: p for p in self._catalogo.produtos_por_sku(list(itens))}
        return [LinhaCarrinho(produtos[sku], quantidade) for sku, quantidade in itens.items() if sku in produtos]
