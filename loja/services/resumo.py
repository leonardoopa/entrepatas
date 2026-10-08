from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .carrinho import LinhaCarrinho
from .frete import ZERO, PoliticaFrete


@dataclass(frozen=True)
class ResumoCompra:
    subtotal: Decimal
    frete: Decimal
    valor_para_frete_gratis: Decimal

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.frete

    @property
    def frete_gratis(self) -> bool:
        return self.subtotal >= self.valor_para_frete_gratis

    @property
    def falta_para_frete_gratis(self) -> Decimal:
        return max(self.valor_para_frete_gratis - self.subtotal, ZERO)

    @property
    def progresso_frete(self) -> int:
        return int(min(self.subtotal / self.valor_para_frete_gratis, 1) * 100)


def montar_resumo(linhas: Iterable[LinhaCarrinho], politica: PoliticaFrete) -> ResumoCompra:
    linhas = list(linhas)
    subtotal = sum((linha.subtotal for linha in linhas), ZERO)
    frete = politica.calcular(subtotal) if linhas else ZERO
    return ResumoCompra(subtotal, frete, politica.valor_para_frete_gratis)
