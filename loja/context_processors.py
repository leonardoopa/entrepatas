import logging

from loja import backoffice
from loja.backoffice.erros import BackofficeIndisponivel
from loja.selectors.catalogo import departamentos_do_menu
from loja.services.carrinho import Carrinho
from loja.services.frete import politica_frete_padrao

logger = logging.getLogger(__name__)


def carrinho_resumo(request):
    return {"carrinho_qtd": len(Carrinho(request.session))}


def navegacao(request):
    try:
        menu = backoffice.obter_catalogo().taxonomia()
    except BackofficeIndisponivel:
        logger.warning("menu_indisponivel")
        menu = []
    return {
        "menu": menu,
        "menu_departamentos": departamentos_do_menu(menu),
        "frete_gratis_acima": politica_frete_padrao().valor_para_frete_gratis,
    }
