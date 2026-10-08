from django.conf import settings

from .carrinho import Carrinho
from .models import Categoria, Departamento, Produto


def carrinho(request):
    return {"carrinho_qtd": len(Carrinho(request))}


def loja(request):
    """Dados do menu: animais, e para cada um os departamentos que têm produtos."""
    pares = Produto.objects.filter(ativo=True, departamento__isnull=False).values_list(
        "categoria_id", "departamento_id"
    ).distinct()
    por_animal = {}
    for cat_id, dep_id in pares:
        por_animal.setdefault(cat_id, set()).add(dep_id)

    departamentos = list(Departamento.objects.all())
    menu = [
        {
            "categoria": c,
            "departamentos": [d for d in departamentos if d.pk in por_animal.get(c.pk, ())],
        }
        for c in Categoria.objects.all()
    ]
    return {
        "menu": menu,
        "menu_departamentos": departamentos,
        "frete_gratis_acima": settings.FRETE_GRATIS_ACIMA,
    }
