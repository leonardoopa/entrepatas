import logging

from django.http import Http404, JsonResponse, QueryDict
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.formats import number_format

from loja.presenters.cena import montar_cena
from loja.repositories import obter_catalogo
from loja.services.catalogo import (
    FAIXAS_VALIDAS, OPCOES_FAIXA, OPCOES_ORDENACAO, ORDEM_PADRAO, ORDENACOES_VALIDAS, Escopo, FiltrosListagem,
    achar_animal, achar_departamento, par_caes_e_gatos, parametros_da_api,
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


def _filtros(params: QueryDict) -> FiltrosListagem:
    faixa, ordem = params.get("faixa", ""), params.get("ordem", ORDEM_PADRAO)
    return FiltrosListagem(
        departamentos=tuple(params.getlist("depto")),
        subdepartamentos=tuple(params.getlist("sub")),
        animais=tuple(params.getlist("animal")),
        marcas=tuple(params.getlist("marca")),
        faixa=faixa if faixa in FAIXAS_VALIDAS else "",
        somente_ofertas=params.get("promo") == "1",
        ordem=ordem if ordem in ORDENACOES_VALIDAS else ORDEM_PADRAO,
    )


def _listagem(request, escopo: Escopo, titulo: str, **contexto):
    filtros = _filtros(request.GET)
    parametros = parametros_da_api(escopo, filtros)
    resultado = obter_catalogo().listar(parametros, _numero_da_pagina(request), POR_PAGINA)
    if escopo.termo and resultado.pagina.total == 0:
        logger.info("busca_sem_resultado termo=%r", escopo.termo)
    consulta = request.GET.copy()
    consulta.pop("pagina", None)
    return render(request, "paginas/catalogo/lista.html", {
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
    catalogo = obter_catalogo()
    menu = catalogo.taxonomia()
    par = par_caes_e_gatos(menu)
    secoes = []
    for item in menu:
        itens = catalogo.listar([("escopo_animal", item.categoria.slug)], 1, ITENS_SECAO_ANIMAL).pagina.itens
        if itens:
            secoes.append((item.categoria, itens))
    return render(request, "paginas/catalogo/home.html", {
        "cena": montar_cena(*par) if par else None,
        "vitrines": catalogo.vitrines(),
        "secoes_animais": secoes[:ANIMAIS_NA_HOME],
        "marcas": catalogo.listar([], 1, 1).facetas.marcas,
    })


def categoria(request, slug):
    animal = achar_animal(obter_catalogo().taxonomia(), slug)
    if animal is None:
        raise Http404
    return _listagem(request, Escopo(animal=slug), f"Tudo para {animal.nome.lower()}", categoria=animal)


def departamento(request, slug):
    dep = achar_departamento(obter_catalogo().taxonomia(), slug)
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
    produtos = obter_catalogo().listar([("q", termo)], 1, ITENS_SUGESTAO).pagina.itens
    return JsonResponse({"itens": [
        {
            "nome": produto.nome,
            "marca": produto.marca,
            "url": produto.get_absolute_url(),
            "preco": number_format(produto.preco_final, 2, use_l10n=True, force_grouping=True),
            "arte": render_to_string("componentes/arte.html", {"p": produto}),
        }
        for produto in produtos
    ]})


def produto(request, slug):
    catalogo = obter_catalogo()
    item = catalogo.produto(slug)
    if item is None:
        raise Http404
    parametros = [("escopo_animal", item.categoria.slug)]
    if item.departamento:
        parametros.append(("departamento", item.departamento.slug))
    relacionados = [
        p for p in catalogo.listar(parametros, 1, ITENS_RELACIONADOS + 1).pagina.itens if p.sku != item.sku
    ][:ITENS_RELACIONADOS]
    return render(request, "paginas/catalogo/produto.html", {"produto": item, "relacionados": relacionados})
