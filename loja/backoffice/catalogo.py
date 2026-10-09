import hashlib
import logging
from collections.abc import Callable, Sequence
from urllib.parse import urlencode

from django.core.cache import BaseCache

from loja.dominio import ItemMenu, ProdutoCatalogo, ResultadoListagem, Vitrine

from . import mapeamento
from .cliente import ClienteBackoffice
from .erros import BackofficeIndisponivel, BackofficeNaoEncontrado

logger = logging.getLogger(__name__)

TTL_RESERVA_SEGUNDOS = 3600
MAXIMO_POR_CONSULTA = 100


class CatalogoBackoffice:
    """Lê o catálogo da API. Respostas ficam em cache; se o backoffice cair, serve a última cópia conhecida."""

    def __init__(self, cliente: ClienteBackoffice, cache: BaseCache, ttl: int = 30):
        self.cliente = cliente
        self.cache = cache
        self.ttl = ttl

    def taxonomia(self) -> list[ItemMenu]:
        return mapeamento.menu(self._consultar("catalogo/taxonomia/"))

    def listar(self, parametros: Sequence[tuple[str, str]], pagina: int, tamanho: int) -> ResultadoListagem:
        dados = self._consultar("catalogo/produtos/", [*parametros, ("pagina", str(pagina)), ("tamanho", str(tamanho))])
        return ResultadoListagem(mapeamento.pagina(dados), mapeamento.facetas(dados.get("facetas", {})))

    def produto(self, slug: str) -> ProdutoCatalogo | None:
        try:
            return mapeamento.produto(self._consultar(f"catalogo/produtos/{slug}/"))
        except BackofficeNaoEncontrado:
            return None

    def produtos_por_sku(self, skus: Sequence[str]) -> list[ProdutoCatalogo]:
        if not skus:
            return []
        parametros = [("sku", sku) for sku in skus] + [("tamanho", str(MAXIMO_POR_CONSULTA))]
        return list(mapeamento.pagina(self._consultar("catalogo/produtos/", parametros)).itens)

    def vitrines(self) -> dict[str, Vitrine]:
        return mapeamento.vitrines(self._consultar("vitrines/"))

    def _consultar(self, caminho: str, parametros: Sequence[tuple[str, str]] | None = None) -> dict:
        chave = self._chave(caminho, parametros)
        return self._com_cache(chave, lambda: self.cliente.get(caminho, parametros))

    def _com_cache(self, chave: str, buscar: Callable[[], dict]) -> dict:
        recente = self.cache.get(f"bo:{chave}")
        if recente is not None:
            return recente
        try:
            dados = buscar()
        except BackofficeIndisponivel:
            antigo = self.cache.get(f"bo-antigo:{chave}")
            if antigo is None:
                raise
            logger.warning("catalogo_servido_do_cache_antigo chave=%s", chave[:12])
            return antigo
        if self.ttl > 0:
            self.cache.set(f"bo:{chave}", dados, self.ttl)
            self.cache.set(f"bo-antigo:{chave}", dados, TTL_RESERVA_SEGUNDOS)
        return dados

    @staticmethod
    def _chave(caminho: str, parametros: Sequence[tuple[str, str]] | None) -> str:
        consulta = urlencode(sorted(parametros or ()))
        return hashlib.sha1(f"{caminho}?{consulta}".encode()).hexdigest()
