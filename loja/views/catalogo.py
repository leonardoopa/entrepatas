import logging

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.formats import number_format

from loja.cena import montar_cena
from loja.models import Categoria, Departamento
from loja.selectors import catalogo as consultas
from loja.selectors.catalogo import OPCOES_FAIXA, OPCOES_ORDENACAO, FiltrosListagem

logger = logging.getLogger(__name__)

POR_PAGINA = 12
ITENS_CARROSSEL = 12
ITENS_SECAO_ANIMAL = 10
ANIMAIS_NA_HOME = 2
TAMANHO_MINIMO_BUSCA = 2


def _listagem(request, base, titulo, **contexto):
    filtros = FiltrosListagem.de_querydict(request.GET)
    produtos = consultas.ordenar(consultas.filtrar(base, filtros), filtros.ordem)
    pagina = Paginator(produtos, POR_PAGINA).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)
    return render(request, "loja/lista.html", {
        "titulo": titulo,
        "pagina": pagina,
        "total": pagina.paginator.count,
        "filtros": filtros,
        "opcoes": consultas.opcoes_de_filtro(base, filtros),
        "ordenacoes": OPCOES_ORDENACAO,
        "faixas": OPCOES_FAIXA,
        "querystring": parametros.urlencode(),
        **contexto,
    })


def home(request):
    par = consultas.par_caes_e_gatos()
    return render(request, "loja/home.html", {
        "cena": montar_cena(*par) if par else None,
        "ofertas": consultas.ofertas(ITENS_CARROSSEL),
        "mais_vendidos": consultas.mais_vendidos(ITENS_CARROSSEL),
        "secoes_animais": consultas.destaques_por_animal(ANIMAIS_NA_HOME, ITENS_SECAO_ANIMAL),
        "marcas": consultas.marcas_disponiveis(),
    })


def categoria(request, slug):
    animal = get_object_or_404(Categoria, slug=slug)
    base = consultas.produtos_ativos().filter(categoria=animal)
    return _listagem(request, base, f"Tudo para {animal.nome.lower()}", categoria=animal)


def departamento(request, slug):
    dep = get_object_or_404(Departamento, slug=slug)
    base = consultas.produtos_ativos().filter(departamento=dep)
    return _listagem(request, base, dep.nome, departamento=dep)


def ofertas(request):
    return _listagem(request, consultas.produtos_em_oferta(), "Ofertas")


def busca(request):
    termo = request.GET.get("q", "").strip()
    base = consultas.buscar(termo)
    if termo and not base.exists():
        logger.info("busca_sem_resultado termo=%r", termo)
    titulo = f"Resultados para “{termo}”" if termo else "Todos os produtos"
    return _listagem(request, base, titulo, termo=termo)


def sugestoes(request):
    termo = request.GET.get("q", "").strip()
    if len(termo) < TAMANHO_MINIMO_BUSCA:
        return JsonResponse({"itens": []})
    return JsonResponse({"itens": [
        {
            "nome": produto.nome,
            "marca": produto.marca,
            "url": produto.get_absolute_url(),
            "preco": number_format(produto.preco_final, 2, use_l10n=True, force_grouping=True),
            "arte": render_to_string("loja/_arte.html", {"p": produto}),
        }
        for produto in consultas.sugerir(termo)
    ]})


def produto(request, slug):
    item = get_object_or_404(consultas.produtos_ativos(), slug=slug)
    return render(request, "loja/produto.html", {
        "produto": item,
        "relacionados": consultas.relacionados(item),
    })
