from django.urls import path

from .views import carrinho, catalogo, checkout, contas

app_name = "loja"

urlpatterns = [
    path("", catalogo.home, name="home"),
    path("busca/", catalogo.busca, name="busca"),
    path("busca/sugestoes/", catalogo.sugestoes, name="sugestoes"),
    path("ofertas/", catalogo.ofertas, name="ofertas"),
    path("categoria/<slug:slug>/", catalogo.categoria, name="categoria"),
    path("departamento/<slug:slug>/", catalogo.departamento, name="departamento"),
    path("produto/<slug:slug>/", catalogo.produto, name="produto"),
    path("carrinho/", carrinho.ver, name="carrinho"),
    path("carrinho/mini/", carrinho.mini, name="minicarrinho"),
    path("carrinho/adicionar/<str:sku>/", carrinho.adicionar, name="carrinho_adicionar"),
    path("carrinho/atualizar/<str:sku>/", carrinho.atualizar, name="carrinho_atualizar"),
    path("carrinho/remover/<str:sku>/", carrinho.remover, name="carrinho_remover"),
    path("checkout/", checkout.finalizar, name="checkout"),
    path("pedido/<str:numero>/", checkout.pedido, name="pedido"),
    path("conta/", contas.conta, name="conta"),
    path("conta/criar/", contas.cadastro, name="cadastro"),
    path("conta/entrar/", contas.EntrarView.as_view(), name="entrar"),
    path("conta/sair/", contas.SairView.as_view(), name="sair"),
    path("conta/senha/recuperar/", contas.RecuperarSenhaView.as_view(), name="senha_recuperar"),
    path("conta/senha/enviado/", contas.SenhaEnviadaView.as_view(), name="senha_enviada"),
    path("conta/senha/redefinir/<uidb64>/<token>/", contas.RedefinirSenhaView.as_view(), name="senha_redefinir"),
    path("conta/senha/concluido/", contas.SenhaConcluidaView.as_view(), name="senha_concluida"),
]
