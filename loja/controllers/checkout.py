import logging

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from loja.models import CheckoutError, CheckoutIndisponivel, ItemIndisponivel
from loja.repositories import obter_catalogo, obter_pedidos
from loja.services.carrinho import Carrinho
from loja.services.checkout import finalizar_pedido, novo_numero_pedido
from loja.services.frete import politica_frete_padrao
from loja.services.resumo import montar_resumo

from .forms import CheckoutForm

logger = logging.getLogger(__name__)

ULTIMO_PEDIDO = "ultimo_pedido"
NUMERO_EM_ANDAMENTO = "checkout_numero"


def _usuario(request):
    return request.user if request.user.is_authenticated else None


def _dados_iniciais(request) -> dict:
    usuario = _usuario(request)
    return {"nome": usuario.get_full_name(), "email": usuario.email} if usuario else {}


def finalizar(request):
    carrinho = Carrinho(request.session, obter_catalogo())
    linhas = carrinho.linhas()
    if not linhas:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("loja:carrinho")

    resumo = montar_resumo(linhas, politica_frete_padrao())
    form = CheckoutForm(request.POST or None, initial=_dados_iniciais(request))
    if request.method == "POST" and form.is_valid():
        numero = request.session.setdefault(NUMERO_EM_ANDAMENTO, novo_numero_pedido())
        request.session.save()
        try:
            criado = finalizar_pedido(
                numero=numero, dados_entrega=form.cleaned_data, linhas=linhas, resumo=resumo,
                pedidos=obter_pedidos(), usuario=_usuario(request),
            )
        except ItemIndisponivel as erro:
            messages.error(request, f"Estoque insuficiente para {erro.nome}.")
            return redirect("loja:carrinho")
        except CheckoutIndisponivel:
            messages.error(request, "Não conseguimos registrar seu pedido agora. Nada foi cobrado. Tente de novo em instantes.")
            return render(request, "paginas/checkout/checkout.html", {"form": form, "linhas": linhas, "resumo": resumo}, status=503)
        except CheckoutError:
            messages.error(request, "Não foi possível finalizar o pedido. Confira os dados e tente de novo.")
            return render(request, "paginas/checkout/checkout.html", {"form": form, "linhas": linhas, "resumo": resumo}, status=422)
        carrinho.limpar()
        request.session.pop(NUMERO_EM_ANDAMENTO, None)
        request.session[ULTIMO_PEDIDO] = criado.numero
        return redirect("loja:pedido", numero=criado.numero)

    return render(request, "paginas/checkout/checkout.html", {"form": form, "linhas": linhas, "resumo": resumo})


def pedido(request, numero):
    item = obter_pedidos().obter(numero)
    if item is None:
        raise Http404
    dono = request.user.is_authenticated and item.cliente_id == str(request.user.pk)
    if request.session.get(ULTIMO_PEDIDO) != numero and not dono:
        logger.warning("pedido_acesso_negado numero=%s", numero)
        return redirect("loja:home")
    return render(request, "paginas/checkout/pedido.html", {"pedido": item})
