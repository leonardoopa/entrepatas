import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from loja.forms import CheckoutForm
from loja.models import Pedido
from loja.services.carrinho import Carrinho
from loja.services.checkout import ItemIndisponivel, finalizar_pedido
from loja.services.frete import politica_frete_padrao
from loja.services.resumo import montar_resumo

logger = logging.getLogger(__name__)

ULTIMO_PEDIDO = "ultimo_pedido"


def _usuario(request):
    return request.user if request.user.is_authenticated else None


def _dados_iniciais(request) -> dict:
    usuario = _usuario(request)
    return {"nome": usuario.get_full_name(), "email": usuario.email} if usuario else {}


def finalizar(request):
    carrinho = Carrinho(request.session)
    linhas = carrinho.linhas()
    if not linhas:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("loja:carrinho")

    form = CheckoutForm(request.POST or None, initial=_dados_iniciais(request))
    if request.method == "POST" and form.is_valid():
        itens = {linha.produto.pk: linha.quantidade for linha in linhas}
        try:
            pedido = finalizar_pedido(dados_entrega=form.cleaned_data, itens=itens, usuario=_usuario(request))
        except ItemIndisponivel as erro:
            messages.error(request, f"Estoque insuficiente para {erro.nome}.")
            return redirect("loja:carrinho")
        carrinho.limpar()
        request.session[ULTIMO_PEDIDO] = pedido.pk
        return redirect("loja:pedido", pk=pedido.pk)

    resumo = montar_resumo(linhas, politica_frete_padrao())
    return render(request, "loja/checkout.html", {"form": form, "linhas": linhas, "resumo": resumo})


def pedido(request, pk):
    item = get_object_or_404(Pedido, pk=pk)
    dono = request.user.is_authenticated and item.usuario_id == request.user.pk
    if request.session.get(ULTIMO_PEDIDO) != pk and not dono:
        logger.warning("pedido_acesso_negado pedido=%s", pk)
        return redirect("loja:home")
    return render(request, "loja/pedido.html", {"pedido": item})
