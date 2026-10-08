import logging
import math
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from loja.models import Categoria

logger = logging.getLogger(__name__)

PASTA_FOTOS = "loja/cena"
PASTA_FOTOS_NO_DISCO = Path(__file__).resolve().parent / "static" / PASTA_FOTOS
EXTENSOES_FOTO = {".jpg", ".jpeg", ".png", ".webp"}
MINIMO_FOTOS = 4
LIMITE_POUCAS_FOTOS = 6
COLUNAS_POUCAS_FOTOS = 2
TAMANHO_DESENHO = (6.5, 8.0)
TAMANHO_FOTO = (8.0, 9.5)
TAMANHO_FOTO_GRANDE = (10.5, 12.0)
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
    foto: str = ""

    @property
    def estilo(self) -> str:
        return f"--x:{self.x:.1f};--y:{self.y:.1f};--s:{self.tamanho:.1f};--r:{self.rotacao};--i:{self.inicio:.3f}"


@dataclass(frozen=True)
class Cena:
    caes: Categoria
    gatos: Categoria
    figuras_caes: list[Figura]
    figuras_gatos: list[Figura]


def listar_fotos(animal: str, pasta: Path = PASTA_FOTOS_NO_DISCO) -> list[str]:
    diretorio = pasta / animal
    if not diretorio.is_dir():
        return []
    arquivos = sorted(a for a in diretorio.iterdir() if a.suffix.lower() in EXTENSOES_FOTO)
    logger.debug("cena_fotos animal=%s quantidade=%d", animal, len(arquivos))
    return [f"{PASTA_FOTOS}/{animal}/{arquivo.name}" for arquivo in arquivos]


def montar_figuras(quantidade: int, lado: Lado, semente: str, fotos: list[str] | None = None) -> list[Figura]:
    sorteio = random.Random(semente)
    fotos = list(fotos or [])
    usar_fotos = len(fotos) >= MINIMO_FOTOS
    sorteio.shuffle(fotos)
    if usar_fotos:
        quantidade = min(quantidade, len(fotos))

    poucas_fotos = usar_fotos and quantidade <= LIMITE_POUCAS_FOTOS
    colunas = COLUNAS_POUCAS_FOTOS if poucas_fotos else COLUNAS
    faixa_tamanho = TAMANHO_FOTO_GRANDE if poucas_fotos else TAMANHO_FOTO if usar_fotos else TAMANHO_DESENHO

    linhas = math.ceil(quantidade / colunas)
    inicio_zona, fim_zona = ZONA_LATERAL
    largura_coluna = (fim_zona - inicio_zona) / colunas
    altura_linha = 100 / linhas

    celulas = [(coluna, linha) for linha in range(linhas) for coluna in range(colunas)][:quantidade]
    inicios = [
        INICIO_PRIMEIRA + (INICIO_ULTIMA - INICIO_PRIMEIRA) * posicao / max(quantidade - 1, 1)
        for posicao in range(quantidade)
    ]
    sorteio.shuffle(inicios)
    variantes = [posicao % VARIANTES for posicao in range(quantidade)]
    sorteio.shuffle(variantes)

    figuras = []
    for posicao, ((coluna, linha), inicio, variante) in enumerate(zip(celulas, inicios, variantes)):
        x = inicio_zona + (coluna + 0.5) * largura_coluna + sorteio.uniform(-0.6, 0.6)
        y = (linha + 0.5) * altura_linha + sorteio.uniform(-3.0, 3.0)
        figuras.append(Figura(
            x=x if lado is Lado.ESQUERDO else 100 - x,
            y=y,
            tamanho=sorteio.uniform(*faixa_tamanho),
            rotacao=sorteio.randint(-14, 14),
            inicio=inicio,
            variante=variante,
            foto=fotos[posicao] if usar_fotos else "",
        ))
    return figuras


def montar_cena(
    caes: Categoria,
    gatos: Categoria,
    quantidade: int = FIGURAS_POR_LADO,
    fotos_caes: list[str] | None = None,
    fotos_gatos: list[str] | None = None,
) -> Cena:
    fotos_caes = listar_fotos("caes") if fotos_caes is None else fotos_caes
    fotos_gatos = listar_fotos("gatos") if fotos_gatos is None else fotos_gatos
    return Cena(
        caes=caes,
        gatos=gatos,
        figuras_caes=montar_figuras(quantidade, Lado.ESQUERDO, "caes", fotos_caes),
        figuras_gatos=montar_figuras(quantidade, Lado.DIREITO, "gatos", fotos_gatos),
    )
