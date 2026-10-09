import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from loja import backoffice
from loja.backoffice.erros import BackofficeIndisponivel
from loja.forms import CadastroForm, LoginForm, RecuperarSenhaForm

logger = logging.getLogger(__name__)


def _destino_seguro(request) -> str:
    destino = request.POST.get("next") or request.GET.get("next") or ""
    permitido = url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return destino if permitido else ""


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("loja:conta")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, f"Conta criada! Bem-vindo(a), {usuario.first_name}.")
        return redirect(_destino_seguro(request) or "loja:conta")
    return render(request, "loja/cadastro.html", {"form": form, "next": _destino_seguro(request)})


@login_required
def conta(request):
    try:
        pedidos = backoffice.obter_pedidos().do_cliente(str(request.user.pk))
    except BackofficeIndisponivel:
        messages.warning(request, "Não conseguimos carregar seus pedidos agora. Tente de novo em instantes.")
        pedidos = []
    return render(request, "loja/conta.html", {"pedidos": pedidos})


class EntrarView(auth_views.LoginView):
    template_name = "loja/entrar.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class SairView(auth_views.LogoutView):
    pass


class RecuperarSenhaView(auth_views.PasswordResetView):
    template_name = "loja/senha_recuperar.html"
    form_class = RecuperarSenhaForm
    email_template_name = "loja/email/senha_recuperar.txt"
    subject_template_name = "loja/email/senha_recuperar_assunto.txt"
    success_url = reverse_lazy("loja:senha_enviada")

    def form_valid(self, form):
        logger.info("recuperacao_senha_solicitada")
        return super().form_valid(form)


class SenhaEnviadaView(auth_views.PasswordResetDoneView):
    template_name = "loja/senha_enviada.html"


class RedefinirSenhaView(auth_views.PasswordResetConfirmView):
    template_name = "loja/senha_redefinir.html"
    success_url = reverse_lazy("loja:senha_concluida")

    def form_valid(self, form):
        logger.info("senha_redefinida usuario=%s", form.user.pk)
        return super().form_valid(form)


class SenhaConcluidaView(auth_views.PasswordResetCompleteView):
    template_name = "loja/senha_concluida.html"
