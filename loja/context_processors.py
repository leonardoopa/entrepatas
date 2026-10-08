from .carrinho import Carrinho
from .models import Categoria


def carrinho(request):
    return {"carrinho_qtd": len(Carrinho(request))}


def categorias(request):
    return {"menu_categorias": Categoria.objects.all()}
