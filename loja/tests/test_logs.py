from django.core import mail
from django.test import TestCase
from django.urls import reverse

from loja.models import Pedido

from .fabricas import DADOS_ENTREGA, SENHA, criar_catalogo, criar_usuario


class LogsTests(TestCase):
    def test_pedido_criado(self):
        produto = criar_catalogo()["bola"]
        self.client.post(reverse("loja:carrinho_adicionar", args=[produto.pk]))
        with self.assertLogs("loja.services.checkout", "INFO") as logs:
            self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertIn(f"pedido_criado pedido={Pedido.objects.get().pk}", logs.output[0])

    def test_estoque_insuficiente_gera_aviso(self):
        c = criar_catalogo()
        self.client.post(reverse("loja:carrinho_adicionar", args=[c["racao"].pk]), {"quantidade": 5})
        c["racao"].__class__.objects.filter(pk=c["racao"].pk).update(estoque=1)
        with self.assertLogs("loja.services.checkout", "WARNING") as logs:
            self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertIn("checkout_item_indisponivel item=Ração", logs.output[0])

    def test_produto_sem_estoque_no_carrinho(self):
        osso = criar_catalogo()["osso"]
        with self.assertLogs("loja.services.carrinho", "WARNING") as logs:
            self.client.post(reverse("loja:carrinho_adicionar", args=[osso.pk]))
        self.assertIn(f"carrinho_produto_sem_estoque produto={osso.pk}", logs.output[0])

    def test_cadastro_login_e_logout(self):
        with self.assertLogs("loja", "INFO") as logs:
            self.client.post(reverse("loja:cadastro"), {
                "nome": "Maria", "email": "maria@example.com", "senha": "Gatinho!2024x", "senha2": "Gatinho!2024x",
            })
            self.client.post(reverse("loja:sair"))
        saida = "\n".join(logs.output)
        self.assertIn("usuario_criado", saida)
        self.assertIn("login_ok", saida)
        self.assertIn("logout", saida)

    def test_login_falho_nao_registra_credenciais(self):
        criar_usuario()
        with self.assertLogs("loja.signals", "WARNING") as logs:
            self.client.post(reverse("loja:entrar"), {"username": "ana@example.com", "password": "errada!Senha1"})
        self.assertIn("login_falhou", logs.output[0])
        self.assertNotIn("ana@example.com", logs.output[0])
        self.assertNotIn("errada", logs.output[0])

    def test_recuperacao_de_senha_nao_registra_email(self):
        criar_usuario()
        with self.assertLogs("loja.views.contas", "INFO") as logs:
            self.client.post(reverse("loja:senha_recuperar"), {"email": "ana@example.com"})
        self.assertIn("recuperacao_senha_solicitada", logs.output[0])
        self.assertNotIn("ana@example.com", logs.output[0])
        self.assertEqual(len(mail.outbox), 1)

    def test_busca_sem_resultado(self):
        with self.assertLogs("loja.views.catalogo", "INFO") as logs:
            self.client.get(reverse("loja:busca"), {"q": "unicornio"})
        self.assertIn("busca_sem_resultado", logs.output[0])
