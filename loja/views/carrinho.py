import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from loja.models import Produto
from loja.services.carrinho import Carrinho, ProdutoSemEstoque
from loja.services.frete import politica_frete_padrao
from loja.services.resumo import montar_resumo

logger = logging.getLogger(__name__)


def _inteiro(valor, padrao: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _em_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _contexto_carrinho(carrinho: Carrinho) -> dict:
    linhas = carrinho.linhas()
    return {"linhas": linhas, "resumo": montar_resumo(linhas, politica_frete_padrao())}


def _resposta_ajax(request, carrinho: Carrinho, mensagem: str, ok: bool = True):
    html = render_to_string("loja/_minicarrinho.html", _contexto_carrinho(carrinho), request=request)
    return JsonResponse(
        {"ok": ok, "mensagem": mensagem, "qtd": len(carrinho), "html": html},
        status=200 if ok else 400,
    )


def _responder(request, carrinho: Carrinho, mensagem: str, destino, ok: bool = True):
    if _em_ajax(request):
        return _resposta_ajax(request, carrinho, mensagem, ok)
    (messages.success if ok else messages.error)(request, mensagem)
    return redirect(destino)


def mini(request):
    return _resposta_ajax(request, Carrinho(request.session), "")


def ver(request):
    return render(request, "loja/carrinho.html", _contexto_carrinho(Carrinho(request.session)))


@require_POST
def adicionar(request, pk):
    produto = get_object_or_404(Produto, pk=pk, ativo=True)
    carrinho = Carrinho(request.session)
    quantidade = max(1, _inteiro(request.POST.get("quantidade"), 1))
    try:
        carrinho.adicionar(produto, quantidade)
    except ProdutoSemEstoque:
        return _responder(request, carrinho, "Produto sem estoque.", produto, ok=False)
    logger.info("carrinho_produto_adicionado produto=%s quantidade=%s", produto.pk, quantidade)
    return _responder(request, carrinho, f"{produto.nome} foi adicionado ao carrinho.", "loja:carrinho")


@require_POST
def atualizar(request, pk):
    produto = get_object_or_404(Produto, pk=pk, ativo=True)
    Carrinho(request.session).definir(produto, _inteiro(request.POST.get("quantidade"), 0))
    return redirect("loja:carrinho")


@require_POST
def remover(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    carrinho = Carrinho(request.session)
    carrinho.remover(produto)
    return _responder(request, carrinho, "Item removido.", "loja:carrinho")
