from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.formats import number_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .carrinho import Carrinho
from .forms import CadastroForm, CheckoutForm
from .models import Categoria, Departamento, ItemPedido, Pedido, Produto

POR_PAGINA = 12

ORDENACOES = {
    "relevancia": ("Mais vendidos", "-vendas"),
    "menor-preco": ("Menor preço", "valor"),
    "maior-preco": ("Maior preço", "-valor"),
    "nome": ("Nome (A-Z)", "nome"),
    "novidades": ("Novidades", "-criado_em"),
}

FAIXAS = {
    "ate-50": ("Até R$ 50", None, 50),
    "50-100": ("R$ 50 a R$ 100", 50, 100),
    "100-200": ("R$ 100 a R$ 200", 100, 200),
    "acima-200": ("Acima de R$ 200", 200, None),
}


def _produtos_ativos():
    return (
        Produto.objects.filter(ativo=True)
        .select_related("categoria", "departamento")
        .annotate(valor=Coalesce("preco_promocional", "preco"))
    )


def _listar(request, base, titulo, **extra):
    """Listagem com filtros (GET), ordenação e paginação sobre o queryset `base`."""
    get = request.GET
    deptos, animais, marcas = get.getlist("depto"), get.getlist("animal"), get.getlist("marca")
    faixa, promo = get.get("faixa", ""), get.get("promo") == "1"
    ordem = get.get("ordem", "relevancia")
    if ordem not in ORDENACOES:
        ordem = "relevancia"

    produtos = base
    if deptos:
        produtos = produtos.filter(departamento__slug__in=deptos)
    if animais:
        produtos = produtos.filter(categoria__slug__in=animais)
    if marcas:
        produtos = produtos.filter(marca__in=marcas)
    if promo:
        produtos = produtos.filter(preco_promocional__isnull=False)
    if faixa in FAIXAS:
        _, minimo, maximo = FAIXAS[faixa]
        if minimo is not None:
            produtos = produtos.filter(valor__gte=minimo)
        if maximo is not None:
            produtos = produtos.filter(valor__lt=maximo)
    produtos = produtos.order_by(ORDENACOES[ordem][1], "nome")

    pagina = Paginator(produtos, POR_PAGINA).get_page(get.get("pagina"))
    sem_pagina = get.copy()
    sem_pagina.pop("pagina", None)

    ativos = bool(deptos or animais or marcas or promo or faixa in FAIXAS)
    return render(request, "loja/lista.html", {
        "titulo": titulo,
        "pagina": pagina,
        "total": pagina.paginator.count,
        "ordem": ordem,
        "ordenacoes": [(k, v[0]) for k, v in ORDENACOES.items()],
        "faixas": [(k, v[0]) for k, v in FAIXAS.items()],
        "faixa": faixa,
        "promo": promo,
        "sel_deptos": deptos,
        "sel_animais": animais,
        "sel_marcas": marcas,
        "facet_deptos": Departamento.objects.filter(pk__in=base.values("departamento")),
        "facet_animais": Categoria.objects.filter(pk__in=base.values("categoria")),
        "facet_marcas": sorted(set(base.exclude(marca="").values_list("marca", flat=True))),
        "filtros_ativos": ativos,
        "querystring": sem_pagina.urlencode(),
        **extra,
    })


def home(request):
    produtos = _produtos_ativos()
    animais = []
    for cat in Categoria.objects.all():
        itens = list(produtos.filter(categoria=cat).order_by("-vendas")[:10])
        if itens:
            animais.append((cat, itens))
    return render(request, "loja/home.html", {
        "ofertas": list(produtos.filter(preco_promocional__isnull=False).order_by("-vendas")[:12]),
        "mais_vendidos": list(produtos.order_by("-vendas")[:12]),
        "secoes_animais": animais[:2],
        "marcas": sorted(set(produtos.exclude(marca="").values_list("marca", flat=True))),
    })


def categoria(request, slug):
    cat = get_object_or_404(Categoria, slug=slug)
    return _listar(request, _produtos_ativos().filter(categoria=cat), f"Tudo para {cat.nome.lower()}",
                   categoria=cat)


def departamento(request, slug):
    dep = get_object_or_404(Departamento, slug=slug)
    return _listar(request, _produtos_ativos().filter(departamento=dep), dep.nome, departamento=dep)


def ofertas(request):
    return _listar(request, _produtos_ativos().filter(preco_promocional__isnull=False), "Ofertas")


def busca(request):
    termo = request.GET.get("q", "").strip()
    base = _produtos_ativos()
    if termo:
        base = base.filter(
            Q(nome__icontains=termo) | Q(marca__icontains=termo) | Q(descricao__icontains=termo)
        )
    titulo = f"Resultados para “{termo}”" if termo else "Todos os produtos"
    return _listar(request, base, titulo, termo=termo)


def sugestoes(request):
    """Autocomplete da busca: até 6 produtos em JSON."""
    termo = request.GET.get("q", "").strip()
    if len(termo) < 2:
        return JsonResponse({"itens": []})
    achados = _produtos_ativos().filter(
        Q(nome__icontains=termo) | Q(marca__icontains=termo)
    ).order_by("-vendas")[:6]
    return JsonResponse({"itens": [
        {
            "nome": p.nome,
            "marca": p.marca,
            "url": p.get_absolute_url(),
            "preco": number_format(p.preco_final, 2, use_l10n=True, force_grouping=True),
            "arte": render_to_string("loja/_arte.html", {"p": p}),
        }
        for p in achados
    ]})


def produto(request, slug):
    item = get_object_or_404(_produtos_ativos(), slug=slug)
    relacionados = (
        _produtos_ativos()
        .filter(Q(departamento=item.departamento) | Q(categoria=item.categoria))
        .exclude(pk=item.pk)
        .order_by("-vendas")[:10]
    )
    return render(request, "loja/produto.html", {"produto": item, "relacionados": relacionados})


# ---------- carrinho ----------

def _ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _resposta_ajax(request, cart, mensagem, ok=True):
    """Estado atual do carrinho para o mini-carrinho (JSON)."""
    linhas = cart.linhas()
    html = render_to_string(
        "loja/_minicarrinho.html", {"linhas": linhas, **Carrinho.calcular(linhas)}, request=request
    )
    return JsonResponse(
        {"ok": ok, "mensagem": mensagem, "qtd": len(cart), "html": html},
        status=200 if ok else 400,
    )


def minicarrinho(request):
    return _resposta_ajax(request, Carrinho(request), "")


def carrinho(request):
    linhas = Carrinho(request).linhas()
    return render(request, "loja/carrinho.html", {"linhas": linhas, **Carrinho.calcular(linhas)})


@require_POST
def carrinho_adicionar(request, pk):
    item = get_object_or_404(Produto, pk=pk, ativo=True)
    cart = Carrinho(request)
    if item.estoque <= 0:
        if _ajax(request):
            return _resposta_ajax(request, cart, "Produto sem estoque.", ok=False)
        messages.error(request, "Produto sem estoque.")
        return redirect(item)
    try:
        quantidade = max(1, int(request.POST.get("quantidade", 1)))
    except ValueError:
        quantidade = 1
    cart.adicionar(item, quantidade)
    if _ajax(request):
        return _resposta_ajax(request, cart, f"{item.nome} foi adicionado ao carrinho.")
    messages.success(request, f"{item.nome} adicionado ao carrinho.")
    return redirect("loja:carrinho")


@require_POST
def carrinho_atualizar(request, pk):
    item = get_object_or_404(Produto, pk=pk, ativo=True)
    try:
        quantidade = int(request.POST.get("quantidade", 0))
    except ValueError:
        quantidade = 0
    Carrinho(request).definir(item, quantidade)
    return redirect("loja:carrinho")


@require_POST
def carrinho_remover(request, pk):
    item = get_object_or_404(Produto, pk=pk)
    cart = Carrinho(request)
    cart.remover(item)
    if _ajax(request):
        return _resposta_ajax(request, cart, "Item removido.")
    return redirect("loja:carrinho")


def checkout(request):
    cart = Carrinho(request)
    linhas = cart.linhas()
    if not linhas:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("loja:carrinho")

    inicial = {}
    if request.user.is_authenticated:
        inicial = {"nome": request.user.get_full_name(), "email": request.user.email}
    form = CheckoutForm(request.POST or None, initial=inicial)
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
            # Totais recalculados com os preços travados.
            totais = Carrinho.calcular(
                [(travados[p.pk], q, travados[p.pk].preco_final * q) for p, q, _ in linhas]
            )
            pedido = form.save(commit=False)
            pedido.frete = totais["frete"]
            if request.user.is_authenticated:
                pedido.usuario = request.user
            pedido.save()
            for produto_, qtd, _ in linhas:
                atual = travados[produto_.pk]
                ItemPedido.objects.create(
                    pedido=pedido, produto=atual, quantidade=qtd,
                    preco_unitario=atual.preco_final,
                )
                atual.estoque -= qtd
                atual.vendas += qtd
                atual.save(update_fields=["estoque", "vendas"])
        cart.limpar()
        request.session["ultimo_pedido"] = pedido.pk
        return redirect("loja:pedido", pk=pedido.pk)

    return render(request, "loja/checkout.html", {"form": form, "linhas": linhas, **Carrinho.calcular(linhas)})


def pedido_confirmado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    # Só o comprador (mesma sessão) ou o dono da conta vê o pedido.
    dono = request.user.is_authenticated and pedido.usuario_id == request.user.pk
    if request.session.get("ultimo_pedido") != pk and not dono:
        return redirect("loja:home")
    return render(request, "loja/pedido.html", {"pedido": pedido})


# ---------- contas ----------

def _destino_seguro(request):
    """Valor de `next` aceito apenas se apontar para este mesmo site."""
    destino = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return destino if ok else ""


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("loja:conta")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)  # a sessão (e o carrinho) continuam
        messages.success(request, f"Conta criada! Bem-vindo(a), {usuario.first_name}.")
        return redirect(_destino_seguro(request) or "loja:conta")
    return render(request, "loja/cadastro.html", {"form": form, "next": _destino_seguro(request)})


@login_required
def conta(request):
    pedidos = request.user.pedidos.prefetch_related("itens__produto")
    return render(request, "loja/conta.html", {"pedidos": pedidos})
