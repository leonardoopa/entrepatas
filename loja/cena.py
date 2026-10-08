import math
import random
from dataclasses import dataclass
from enum import Enum

from loja.models import Categoria

FIGURAS_POR_LADO = 12
COLUNAS = 3
VARIANTES = 6
ZONA_LATERAL = (4.0, 33.0)
INICIO_PRIMEIRA = 0.04
INICIO_ULTIMA = 0.72


class Lado(Enum):
    ESQUERDO = "esquerdo"
    DIREITO = "direito"


@dataclass(frozen=True)
class Figura:
    x: float
    y: float
    tamanho: float
    rotacao: int
    inicio: float
    variante: int

    @property
    def estilo(self) -> str:
        return f"--x:{self.x:.1f};--y:{self.y:.1f};--s:{self.tamanho:.1f};--r:{self.rotacao};--i:{self.inicio:.3f}"


@dataclass(frozen=True)
class Cena:
    caes: Categoria
    gatos: Categoria
    figuras_caes: list[Figura]
    figuras_gatos: list[Figura]


def montar_figuras(quantidade: int, lado: Lado, semente: str) -> list[Figura]:
    sorteio = random.Random(semente)
    linhas = math.ceil(quantidade / COLUNAS)
    inicio_zona, fim_zona = ZONA_LATERAL
    largura_coluna = (fim_zona - inicio_zona) / COLUNAS
    altura_linha = 100 / linhas

    celulas = [(coluna, linha) for linha in range(linhas) for coluna in range(COLUNAS)][:quantidade]
    inicios = [
        INICIO_PRIMEIRA + (INICIO_ULTIMA - INICIO_PRIMEIRA) * posicao / max(quantidade - 1, 1)
        for posicao in range(quantidade)
    ]
    sorteio.shuffle(inicios)
    variantes = [posicao % VARIANTES for posicao in range(quantidade)]
    sorteio.shuffle(variantes)

    figuras = []
    for (coluna, linha), inicio, variante in zip(celulas, inicios, variantes):
        x = inicio_zona + (coluna + 0.5) * largura_coluna + sorteio.uniform(-0.6, 0.6)
        y = (linha + 0.5) * altura_linha + sorteio.uniform(-3.0, 3.0)
        figuras.append(Figura(
            x=x if lado is Lado.ESQUERDO else 100 - x,
            y=y,
            tamanho=sorteio.uniform(6.5, 8.0),
            rotacao=sorteio.randint(-14, 14),
            inicio=inicio,
            variante=variante,
        ))
    return figuras


def montar_cena(caes: Categoria, gatos: Categoria, quantidade: int = FIGURAS_POR_LADO) -> Cena:
    return Cena(
        caes=caes,
        gatos=gatos,
        figuras_caes=montar_figuras(quantidade, Lado.ESQUERDO, "caes"),
        figuras_gatos=montar_figuras(quantidade, Lado.DIREITO, "gatos"),
    )
