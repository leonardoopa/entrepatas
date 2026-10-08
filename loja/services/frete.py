from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.conf import settings

ZERO = Decimal("0")


class PoliticaFrete(Protocol):
    valor_para_frete_gratis: Decimal

    def calcular(self, subtotal: Decimal) -> Decimal: ...


@dataclass(frozen=True)
class FreteFixoComMinimoGratis:
    valor_fixo: Decimal
    valor_para_frete_gratis: Decimal

    def calcular(self, subtotal: Decimal) -> Decimal:
        return ZERO if subtotal >= self.valor_para_frete_gratis else self.valor_fixo


def politica_frete_padrao() -> PoliticaFrete:
    return FreteFixoComMinimoGratis(settings.FRETE_FIXO, settings.FRETE_GRATIS_ACIMA)
