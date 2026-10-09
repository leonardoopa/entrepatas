import logging

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.formats import number_format

from loja import backoffice
from loja.cena import montar_cena
from loja.selectors.catalogo import (
    OPCOES_FAIXA, OPCOES_ORDENACAO, Escopo, FiltrosListagem, achar_animal, achar_departamento, par_caes_e_gatos,
    parametros_da_api,
)

logger = logging.getLogger(__name__)

POR_PAGINA = 12
ITENS_SECAO_ANIMAL = 10
ANIMAIS_NA_HOME = 2
TAMANHO_MINIMO_BUSCA = 2
ITENS_SUGESTAO = 6
ITENS_RELACIONADOS = 10


def _numero_da_pagina(request) -> int:
    try:
        return max(1, int(request.GET.get("pagina", 1)))
    except ValueError:
        return 1


def _listagem(request, escopo: Escopo, titulo: str, **contexto):
    filtros = FiltrosListagem.de_querydict(request.GET)
    parametros = parametros_da_api(escopo, filtros)
    resultado = backoffice.obter_catalogo().listar(parametros, _numero_da_pagina(request), POR_PAGINA)
    if escopo.termo and resultado.pagina.total == 0:
        logger.info("busca_sem_resultado termo=%r", escopo.termo)
    consulta = request.GET.copy()
    consulta.pop("pagina", None)
    return render(request, "loja/lista.html", {
        "titulo": titulo,
        "pagina": resultado.pagina,
        "total": resultado.pagina.total,
        "filtros": filtros,
        "opcoes": resultado.facetas,
        "ordenacoes": OPCOES_ORDENACAO,
        "faixas": OPCOES_FAIXA,
        "querystring": consulta.urlencode(),
        **contexto,
    })


def home(request):
    catalogo = backoffice.obter_catalogo()
    menu = catalogo.taxonomia()
    par = par_caes_e_gatos(menu)
    secoes = []
    for item in menu:
        itens = catalogo.listar([("escopo_animal", item.categoria.slug)], 1, ITENS_SECAO_ANIMAL).pagina.itens
        if itens:
            secoes.append((item.categoria, itens))
    return render(request, "loja/home.html", {
        "cena": montar_cena(*par) if par else None,
        "vitrines": catalogo.vitrines(),
        "secoes_animais": secoes[:ANIMAIS_NA_HOME],
        "marcas": catalogo.listar([], 1, 1).facetas.marcas,
    })


def categoria(request, slug):
    animal = achar_animal(backoffice.obter_catalogo().taxonomia(), slug)
    if animal is None:
        raise Http404
    return _listagem(request, Escopo(animal=slug), f"Tudo para {animal.nome.lower()}", categoria=animal)


def departamento(request, slug):
    dep = achar_departamento(backoffice.obter_catalogo().taxonomia(), slug)
    if dep is None:
        raise Http404
    return _listagem(request, Escopo(departamento=slug), dep.nome, departamento=dep)


def ofertas(request):
    return _listagem(request, Escopo(ofertas=True), "Ofertas")


def busca(request):
    termo = request.GET.get("q", "").strip()
    titulo = f"Resultados para “{termo}”" if termo else "Todos os produtos"
    return _listagem(request, Escopo(termo=termo), titulo, termo=termo)


def sugestoes(request):
    termo = request.GET.get("q", "").strip()
    if len(termo) < TAMANHO_MINIMO_BUSCA:
        return JsonResponse({"itens": []})
    produtos = backoffice.obter_catalogo().listar([("q", termo)], 1, ITENS_SUGESTAO).pagina.itens
    return JsonResponse({"itens": [
        {
            "nome": produto.nome,
            "marca": produto.marca,
            "url": produto.get_absolute_url(),
            "preco": number_format(produto.preco_final, 2, use_l10n=True, force_grouping=True),
            "arte": render_to_string("loja/_arte.html", {"p": produto}),
        }
        for produto in produtos
    ]})


def produto(request, slug):
    catalogo = backoffice.obter_catalogo()
    item = catalogo.produto(slug)
    if item is None:
        raise Http404
    parametros = [("escopo_animal", item.categoria.slug)]
    if item.departamento:
        parametros.append(("departamento", item.departamento.slug))
    relacionados = [
        p for p in catalogo.listar(parametros, 1, ITENS_RELACIONADOS + 1).pagina.itens if p.sku != item.sku
    ][:ITENS_RELACIONADOS]
    return render(request, "loja/produto.html", {"produto": item, "relacionados": relacionados})
