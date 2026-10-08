import logging
from collections.abc import MutableMapping
from dataclasses import dataclass
from decimal import Decimal

from loja.models import Produto

logger = logging.getLogger(__name__)

SESSION_KEY = "carrinho"


class ProdutoSemEstoque(Exception):
    def __init__(self, produto: Produto):
        super().__init__(f"Produto sem estoque: {produto.pk}")
        self.produto = produto


@dataclass(frozen=True)
class LinhaCarrinho:
    produto: Produto
    quantidade: int

    @property
    def subtotal(self) -> Decimal:
        return self.produto.preco_final * self.quantidade


class Carrinho:
    """Carrinho guardado na sessão como {produto_id: quantidade}."""

    def __init__(self, sessao: MutableMapping):
        self._sessao = sessao

    @property
    def itens(self) -> dict[int, int]:
        return {int(pk): qtd for pk, qtd in self._sessao.get(SESSION_KEY, {}).items()}

    def __len__(self) -> int:
        return sum(self.itens.values())

    def adicionar(self, produto: Produto, quantidade: int = 1) -> None:
        if produto.estoque <= 0:
            logger.warning("carrinho_produto_sem_estoque produto=%s", produto.pk)
            raise ProdutoSemEstoque(produto)
        self.definir(produto, self.itens.get(produto.pk, 0) + quantidade)

    def definir(self, produto: Produto, quantidade: int) -> None:
        itens = self.itens
        quantidade = min(quantidade, produto.estoque)
        if quantidade > 0:
            itens[produto.pk] = quantidade
        else:
            itens.pop(produto.pk, None)
        self._gravar(itens)
        logger.debug("carrinho_item_definido produto=%s quantidade=%s", produto.pk, max(quantidade, 0))

    def remover(self, produto: Produto) -> None:
        itens = self.itens
        itens.pop(produto.pk, None)
        self._gravar(itens)
        logger.debug("carrinho_item_removido produto=%s", produto.pk)

    def limpar(self) -> None:
        self._sessao.pop(SESSION_KEY, None)

    def linhas(self) -> list[LinhaCarrinho]:
        itens = self.itens
        produtos = Produto.objects.filter(pk__in=itens, ativo=True).select_related("categoria")
        return [LinhaCarrinho(produto, itens[produto.pk]) for produto in produtos]

    def _gravar(self, itens: dict[int, int]) -> None:
        self._sessao[SESSION_KEY] = {str(pk): quantidade for pk, quantidade in itens.items()}
