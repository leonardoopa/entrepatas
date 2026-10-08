from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "loja"

urlpatterns = [
    path("", views.home, name="home"),
    path("busca/", views.busca, name="busca"),
    path("busca/sugestoes/", views.sugestoes, name="sugestoes"),
    path("ofertas/", views.ofertas, name="ofertas"),
    path("categoria/<slug:slug>/", views.categoria, name="categoria"),
    path("departamento/<slug:slug>/", views.departamento, name="departamento"),
    path("produto/<slug:slug>/", views.produto, name="produto"),
    path("carrinho/", views.carrinho, name="carrinho"),
    path("carrinho/mini/", views.minicarrinho, name="minicarrinho"),
    path("carrinho/adicionar/<int:pk>/", views.carrinho_adicionar, name="carrinho_adicionar"),
    path("carrinho/atualizar/<int:pk>/", views.carrinho_atualizar, name="carrinho_atualizar"),
    path("carrinho/remover/<int:pk>/", views.carrinho_remover, name="carrinho_remover"),
    path("checkout/", views.checkout, name="checkout"),
    path("pedido/<int:pk>/", views.pedido_confirmado, name="pedido"),
    path("conta/", views.conta, name="conta"),
    path("conta/criar/", views.cadastro, name="cadastro"),
    path(
        "conta/entrar/",
        auth_views.LoginView.as_view(
            template_name="loja/entrar.html", authentication_form=LoginForm, redirect_authenticated_user=True,
        ),
        name="entrar",
    ),
    path("conta/sair/", auth_views.LogoutView.as_view(), name="sair"),
]
