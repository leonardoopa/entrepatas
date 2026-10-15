from functools import lru_cache

from django.conf import settings
from django.core.cache import caches

from .backoffice.catalogo import CatalogoBackoffice
from .backoffice.cliente import ClienteBackoffice
from .backoffice.pedidos import PedidosBackoffice
from .contratos import CatalogoRepositorio, PedidosRepositorio


@lru_cache(maxsize=1)
def _cliente() -> ClienteBackoffice:
    return ClienteBackoffice(settings.BACKOFFICE_URL, settings.BACKOFFICE_API_KEY, settings.BACKOFFICE_TIMEOUT)


def obter_catalogo() -> CatalogoRepositorio:
    return CatalogoBackoffice(_cliente(), caches["default"], settings.BACKOFFICE_CACHE_SEGUNDOS)


def obter_pedidos() -> PedidosRepositorio:
    return PedidosBackoffice(_cliente())
