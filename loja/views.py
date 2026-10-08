from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .carrinho import Carrinho
from .forms import CheckoutForm
from .models import Categoria, ItemPedido, Pedido, Produto

ORDENACOES = {
    "nome": "nome",
    "menor-preco": "preco",
    "maior-preco": "-preco",
    "novidades": "-criado_em",
}


def _produtos_ativos():
    return Produto.objects.filter(ativo=True).select_related("categoria")


def _ordenar(request, queryset):
    chave = request.GET.get("ordem", "nome")
    return queryset.order_by(ORDENACOES.get(chave, "nome")), chave


def home(request):
    produtos = _produtos_ativos()
    return render(request, "loja/home.html", {
        "destaques": produtos.filter(destaque=True)[:8],
        "promocoes": [p for p in produtos.filter(preco_promocional__isnull=False)[:8] if p.em_promocao],
    })


def categoria(request, slug):
    cat = get_object_or_404(Categoria, slug=slug)
    produtos, ordem = _ordenar(request, _produtos_ativos().filter(categoria=cat))
    return render(request, "loja/lista.html", {
        "titulo": cat.nome, "produtos": produtos, "ordem": ordem,
    })


def busca(request):
    termo = request.GET.get("q", "").strip()
    produtos = _produtos_ativos()
    if termo:
        produtos = produtos.filter(
            Q(nome__icontains=termo) | Q(marca__icontains=termo) | Q(descricao__icontains=termo)
        )
    else:
        produtos = produtos.none()
    produtos, ordem = _ordenar(request, produtos)
    return render(request, "loja/lista.html", {
        "titulo": f"Resultados para “{termo}”" if termo else "Busca",
        "produtos": produtos, "ordem": ordem, "termo": termo,
    })


def produto(request, slug):
    item = get_object_or_404(_produtos_ativos(), slug=slug)
    relacionados = _produtos_ativos().filter(categoria=item.categoria).exclude(pk=item.pk)[:4]
    return render(request, "loja/produto.html", {"produto": item, "relacionados": relacionados})


def carrinho(request):
    cart = Carrinho(request)
    return render(request, "loja/carrinho.html", {"linhas": cart.linhas(), "total": cart.total})


@require_POST
def carrinho_adicionar(request, pk):
    item = get_object_or_404(Produto, pk=pk, ativo=True)
    if item.estoque <= 0:
        messages.error(request, "Produto sem estoque.")
        return redirect(item)
    quantidade = max(1, int(request.POST.get("quantidade", 1) or 1))
    Carrinho(request).adicionar(item, quantidade)
    messages.success(request, f"{item.nome} adicionado ao carrinho.")
    return redirect("loja:carrinho")


@require_POST
def carrinho_atualizar(request, pk):
    item = get_object_or_404(Produto, pk=pk, ativo=True)
    Carrinho(request).definir(item, request.POST.get("quantidade", 0) or 0)
    return redirect("loja:carrinho")


@require_POST
def carrinho_remover(request, pk):
    item = get_object_or_404(Produto, pk=pk)
    Carrinho(request).remover(item)
    return redirect("loja:carrinho")


def checkout(request):
    cart = Carrinho(request)
    linhas = cart.linhas()
    if not linhas:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("loja:carrinho")

    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Trava as linhas de produto para não vender além do estoque.
            travados = {
                p.pk: p
                for p in Produto.objects.select_for_update().filter(
                    pk__in=[p.pk for p, _, _ in linhas], ativo=True
                )
            }
            for produto_, qtd, _ in linhas:
                atual = travados.get(produto_.pk)
                if atual is None or atual.estoque < qtd:
                    messages.error(request, f"Estoque insuficiente para {produto_.nome}.")
                    return redirect("loja:carrinho")
            pedido = form.save()
            for produto_, qtd, _ in linhas:
                atual = travados[produto_.pk]
                ItemPedido.objects.create(
                    pedido=pedido, produto=atual, quantidade=qtd,
                    preco_unitario=atual.preco_final,
                )
                atual.estoque -= qtd
                atual.save(update_fields=["estoque"])
        cart.limpar()
        request.session["ultimo_pedido"] = pedido.pk
        return redirect("loja:pedido", pk=pedido.pk)

    return render(request, "loja/checkout.html", {"form": form, "linhas": linhas, "total": cart.total})


def pedido_confirmado(request, pk):
    # Só o comprador (mesma sessão) vê a confirmação.
    if request.session.get("ultimo_pedido") != pk:
        return redirect("loja:home")
    pedido = get_object_or_404(Pedido, pk=pk)
    return render(request, "loja/pedido.html", {"pedido": pedido})
