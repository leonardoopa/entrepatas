from django.urls import path

from . import views

app_name = "loja"

urlpatterns = [
    path("", views.home, name="home"),
    path("busca/", views.busca, name="busca"),
    path("categoria/<slug:slug>/", views.categoria, name="categoria"),
    path("produto/<slug:slug>/", views.produto, name="produto"),
    path("carrinho/", views.carrinho, name="carrinho"),
    path("carrinho/adicionar/<int:pk>/", views.carrinho_adicionar, name="carrinho_adicionar"),
    path("carrinho/atualizar/<int:pk>/", views.carrinho_atualizar, name="carrinho_atualizar"),
    path("carrinho/remover/<int:pk>/", views.carrinho_remover, name="carrinho_remover"),
    path("checkout/", views.checkout, name="checkout"),
    path("pedido/<int:pk>/", views.pedido_confirmado, name="pedido"),
]
