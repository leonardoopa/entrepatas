from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from loja.models import Pedido, Produto

from .fabricas import DADOS_ENTREGA, criar_catalogo, criar_usuario

AJAX = {"X-Requested-With": "XMLHttpRequest"}


class CarrinhoViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c = criar_catalogo()

    def adicionar(self, produto, **dados):
        return self.client.post(reverse("loja:carrinho_adicionar", args=[produto.pk]), dados)

    def test_nao_adiciona_sem_estoque(self):
        self.adicionar(self.c["osso"])
        self.assertFalse(self.client.session.get("carrinho"))

    def test_limita_ao_estoque(self):
        self.adicionar(self.c["racao"], quantidade=99)
        self.assertEqual(self.client.session["carrinho"], {str(self.c["racao"].pk): 5})

    def test_quantidade_invalida_vira_um(self):
        self.adicionar(self.c["racao"], quantidade="abc")
        self.assertEqual(self.client.session["carrinho"], {str(self.c["racao"].pk): 1})

    def test_adicionar_via_ajax_devolve_json(self):
        resposta = self.client.post(
            reverse("loja:carrinho_adicionar", args=[self.c["bola"].pk]), {"quantidade": 2}, headers=AJAX,
        )
        dados = resposta.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["qtd"], 2)
        self.assertIn("Bola", dados["html"])

    def test_ajax_sem_estoque_devolve_erro(self):
        resposta = self.client.post(reverse("loja:carrinho_adicionar", args=[self.c["osso"].pk]), headers=AJAX)
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(resposta.json()["ok"])

    def test_remover_item(self):
        self.adicionar(self.c["bola"])
        self.client.post(reverse("loja:carrinho_remover", args=[self.c["bola"].pk]))
        self.assertFalse(self.client.session.get("carrinho"))

    def test_resumo_com_frete_cobrado(self):
        self.adicionar(self.c["bola"])
        resumo = self.client.get(reverse("loja:carrinho")).context["resumo"]
        self.assertEqual((resumo.frete, resumo.total), (Decimal("19.90"), Decimal("49.90")))
        self.assertEqual(resumo.falta_para_frete_gratis, Decimal("169.00"))

    def test_resumo_com_frete_gratis(self):
        self.adicionar(self.c["racao_gato"])
        resumo = self.client.get(reverse("loja:carrinho")).context["resumo"]
        self.assertTrue(resumo.frete_gratis)
        self.assertEqual(resumo.frete, Decimal("0"))


class CheckoutViewsTests(TestCase):
    def setUp(self):
        self.c = criar_catalogo()

    def adicionar(self, produto, quantidade=1):
        self.client.post(reverse("loja:carrinho_adicionar", args=[produto.pk]), {"quantidade": quantidade})

    def test_compra_completa(self):
        self.adicionar(self.c["racao"], 2)
        resposta = self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        pedido = Pedido.objects.get()
        self.assertRedirects(resposta, reverse("loja:pedido", args=[pedido.pk]))
        self.assertEqual((pedido.uf, pedido.frete, pedido.total), ("SP", Decimal("19.90"), Decimal("179.90")))
        self.c["racao"].refresh_from_db()
        self.assertEqual(self.c["racao"].estoque, 3)
        self.assertFalse(self.client.session.get("carrinho"))

    def test_frete_gratis_no_pedido(self):
        self.adicionar(self.c["racao_gato"])
        self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertEqual(Pedido.objects.get().frete, Decimal("0"))

    def test_nao_vende_alem_do_estoque(self):
        self.adicionar(self.c["racao"], 5)
        Produto.objects.filter(pk=self.c["racao"].pk).update(estoque=1)
        resposta = self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertRedirects(resposta, reverse("loja:carrinho"))
        self.assertEqual(Pedido.objects.count(), 0)

    def test_formulario_invalido_nao_cria_pedido(self):
        self.adicionar(self.c["bola"])
        resposta = self.client.post(reverse("loja:checkout"), {**DADOS_ENTREGA, "email": "invalido"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_carrinho_vazio_redireciona(self):
        self.assertRedirects(self.client.get(reverse("loja:checkout")), reverse("loja:carrinho"))

    def test_pedido_so_para_o_comprador(self):
        pedido = Pedido.objects.create(nome="Ana", email="a@e.com", cep="1", endereco="x", cidade="y", uf="SP")
        self.assertRedirects(self.client.get(reverse("loja:pedido", args=[pedido.pk])), reverse("loja:home"))

    def test_pedido_logado_fica_na_conta_do_dono(self):
        usuario = criar_usuario()
        self.client.force_login(usuario)
        self.adicionar(self.c["bola"])
        formulario = self.client.get(reverse("loja:checkout")).context["form"]
        self.assertEqual(formulario.initial["email"], "ana@example.com")

        self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.usuario, usuario)
        self.assertContains(self.client.get(reverse("loja:conta")), f"Pedido #{pedido.pk}")

        outro = self.client_class()
        outro.force_login(criar_usuario("c@example.com", "Carla"))
        self.assertRedirects(outro.get(reverse("loja:pedido", args=[pedido.pk])), reverse("loja:home"))
        self.assertNotContains(outro.get(reverse("loja:conta")), f"Pedido #{pedido.pk}")

        self.client.logout()
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("loja:pedido", args=[pedido.pk])).status_code, 200)
