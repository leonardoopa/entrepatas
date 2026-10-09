from loja.models import Departamento
from loja.selectors.catalogo import menu_por_animal
from loja.services.carrinho import Carrinho
from loja.services.frete import politica_frete_padrao


def carrinho_resumo(request):
    return {"carrinho_qtd": len(Carrinho(request.session))}


def navegacao(request):
    return {
        "menu": menu_por_animal(),
        "menu_departamentos": Departamento.objects.all(),
        "frete_gratis_acima": politica_frete_padrao().valor_para_frete_gratis,
    }
