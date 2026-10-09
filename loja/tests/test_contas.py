import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .fabricas import SENHA, BackofficeTestCase, criar_usuario

User = get_user_model()

CADASTRO = {"nome": "Maria", "email": "Maria@Example.com", "senha": "Gatinho!2024x", "senha2": "Gatinho!2024x"}


class CadastroTests(BackofficeTestCase):
    def test_cria_usuario_e_faz_login(self):
        resposta = self.client.post(reverse("loja:cadastro"), CADASTRO)
        self.assertRedirects(resposta, reverse("loja:conta"))
        usuario = User.objects.get(username="maria@example.com")
        self.assertEqual(usuario.first_name, "Maria")
        self.assertTrue(usuario.check_password("Gatinho!2024x"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_mantem_o_carrinho(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=["BOL-1"]))
        self.client.post(reverse("loja:cadastro"), CADASTRO)
        self.assertEqual(self.client.session["carrinho"], {"BOL-1": 1})

    def test_rejeita_email_repetido(self):
        criar_usuario()
        resposta = self.client.post(reverse("loja:cadastro"), {**CADASTRO, "email": "ANA@example.com"})
        self.assertContains(resposta, "Já existe uma conta com este e-mail.")

    def test_rejeita_senha_fraca_e_senhas_diferentes(self):
        url = reverse("loja:cadastro")
        resposta = self.client.post(url, {**CADASTRO, "senha": "12345678", "senha2": "12345678"})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(User.objects.filter(username="maria@example.com").exists())
        self.assertContains(self.client.post(url, {**CADASTRO, "senha2": "outra"}), "As senhas não são iguais.")

    def test_ignora_next_externo(self):
        resposta = self.client.post(reverse("loja:cadastro"), {**CADASTRO, "next": "https://evil.example/x"})
        self.assertRedirects(resposta, reverse("loja:conta"))
        self.client.logout()
        resposta = self.client.post(reverse("loja:cadastro"), {**CADASTRO, "email": "b@example.com", "next": "/carrinho/"})
        self.assertRedirects(resposta, reverse("loja:carrinho"))


class LoginTests(BackofficeTestCase):
    def setUp(self):
        self.usuario = criar_usuario()

    def test_login_com_email_e_senha(self):
        url = reverse("loja:entrar")
        resposta = self.client.post(url, {"username": "ANA@example.com", "password": SENHA})
        self.assertRedirects(resposta, reverse("loja:conta"))
        self.client.logout()
        resposta = self.client.post(url, {"username": "ana@example.com", "password": "errada"})
        self.assertContains(resposta, "E-mail ou senha incorretos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_so_por_post(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("loja:sair")).status_code, 405)
        self.client.post(reverse("loja:sair"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_conta_exige_login(self):
        resposta = self.client.get(reverse("loja:conta"))
        self.assertRedirects(resposta, f"{reverse('loja:entrar')}?next={reverse('loja:conta')}")

    def test_cabecalho_muda_com_login(self):
        self.assertContains(self.client.get(reverse("loja:home")), "Cadastre-se")
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("loja:home"))
        self.assertContains(resposta, "Olá,")
        self.assertContains(resposta, reverse("loja:sair"))

    def test_cabecalho_usa_logo_e_favicon(self):
        html = self.client.get(reverse("loja:home")).content.decode()
        self.assertIn("loja/logo.png", html)
        self.assertIn("loja/favicon.png", html)


class RecuperarSenhaTests(BackofficeTestCase):
    NOVA_SENHA = "NovaSenha!987xy"

    def setUp(self):
        criar_usuario()

    def pedir_link(self, email="ana@example.com"):
        self.client.post(reverse("loja:senha_recuperar"), {"email": email})
        achado = re.search(r"https?://testserver(/conta/senha/redefinir/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(achado, mail.outbox[0].body)
        return achado.group(1)

    def abrir_formulario(self, link):
        return self.client.get(link, follow=True)

    def redefinir(self, resposta, senha):
        return self.client.post(resposta.request["PATH_INFO"], {"new_password1": senha, "new_password2": senha})

    def test_fluxo_completo(self):
        resposta = self.client.post(reverse("loja:senha_recuperar"), {"email": "ana@example.com"})
        self.assertRedirects(resposta, reverse("loja:senha_enviada"))
        self.assertEqual(mail.outbox[0].to, ["ana@example.com"])
        self.assertIn("Olá, Ana!", mail.outbox[0].body)
        mail.outbox.clear()

        formulario = self.abrir_formulario(self.pedir_link())
        self.assertTrue(formulario.context["validlink"])
        self.assertRedirects(self.redefinir(formulario, self.NOVA_SENHA), reverse("loja:senha_concluida"))
        self.assertFalse(self.client.login(username="ana@example.com", password=SENHA))
        self.assertTrue(self.client.login(username="ana@example.com", password=self.NOVA_SENHA))

    def test_link_so_funciona_uma_vez(self):
        link = self.pedir_link()
        self.redefinir(self.abrir_formulario(link), self.NOVA_SENHA)
        resposta = self.abrir_formulario(link)
        self.assertFalse(resposta.context["validlink"])
        self.assertContains(resposta, "Link inválido")

    def test_link_invalido(self):
        resposta = self.client.get(reverse("loja:senha_redefinir", args=["abc", "token-falso"]), follow=True)
        self.assertContains(resposta, "Link inválido")

    def test_email_desconhecido_nao_revela_nada(self):
        resposta = self.client.post(reverse("loja:senha_recuperar"), {"email": "ninguem@example.com"})
        self.assertRedirects(resposta, reverse("loja:senha_enviada"))
        self.assertEqual(len(mail.outbox), 0)

    def test_senha_fraca_e_rejeitada(self):
        resposta = self.redefinir(self.abrir_formulario(self.pedir_link()), "12345678")
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(User.objects.get(username="ana@example.com").check_password(SENHA))

    def test_login_tem_link_para_recuperar(self):
        self.assertContains(self.client.get(reverse("loja:entrar")), reverse("loja:senha_recuperar"))
