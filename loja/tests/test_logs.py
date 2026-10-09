from django.core import mail
from django.urls import reverse

from .fabricas import DADOS_ENTREGA, BackofficeTestCase, criar_usuario


class LogsTests(BackofficeTestCase):
    def test_pedido_criado(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=["BOL-1"]))
        with self.assertLogs("loja.services.checkout", "INFO") as logs:
            self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertIn(f"pedido_criado numero={next(iter(self.bo.pedidos))}", logs.output[0])

    def test_estoque_insuficiente_gera_aviso(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=["RAC-1"]), {"quantidade": 5})
        self.bo.produtos[0]["estoque"] = 1
        with self.assertLogs("loja.services.checkout", "WARNING") as logs:
            self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertIn("checkout_item_indisponivel sku=RAC-1", logs.output[0])

    def test_produto_sem_estoque_no_carrinho(self):
        with self.assertLogs("loja.services.carrinho", "WARNING") as logs:
            self.client.post(reverse("loja:carrinho_adicionar", args=["OSS-1"]))
        self.assertIn("carrinho_produto_sem_estoque sku=OSS-1", logs.output[0])

    def test_produto_adicionado(self):
        with self.assertLogs("loja.views.carrinho", "INFO") as logs:
            self.client.post(reverse("loja:carrinho_adicionar", args=["BOL-1"]), {"quantidade": 2})
        self.assertIn("carrinho_produto_adicionado sku=BOL-1 quantidade=2", logs.output[0])

    def test_backoffice_inacessivel_vira_aviso_sem_expor_dados(self):
        from unittest.mock import patch

        import requests

        from loja.backoffice.cliente import ClienteBackoffice

        cliente = ClienteBackoffice("http://bo/api/v1", "chave-secreta")
        with patch.object(cliente.sessao, "request", side_effect=requests.ConnectionError("x")):
            with self.assertLogs("loja.backoffice.cliente", "WARNING") as logs:
                with self.assertRaises(Exception):
                    cliente.get("vitrines/")
        self.assertIn("backoffice_inacessivel", logs.output[0])
        self.assertNotIn("chave-secreta", logs.output[0])

    def test_site_sem_backoffice_registra_erro(self):
        self.bo.indisponivel = True
        with self.assertLogs("loja.middleware", "ERROR") as logs:
            self.client.get(reverse("loja:busca"))
        self.assertIn("site_sem_backoffice caminho=/busca/", logs.output[0])

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
