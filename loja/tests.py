from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Pedido, Produto


class LojaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Categoria.objects.create(nome="Cães", slug="caes", emoji="🐶")
        cls.racao = Produto.objects.create(
            categoria=cls.cat, nome="Ração", slug="racao", marca="X",
            preco=Decimal("100.00"), preco_promocional=Decimal("80.00"), estoque=5,
        )
        cls.sem_estoque = Produto.objects.create(
            categoria=cls.cat, nome="Osso", slug="osso", preco=Decimal("10.00"), estoque=0,
        )

    def test_paginas_publicas(self):
        for url in [
            reverse("loja:home"),
            self.cat.get_absolute_url(),
            self.racao.get_absolute_url(),
            reverse("loja:busca") + "?q=ra",
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_preco_promocional(self):
        self.assertEqual(self.racao.preco_final, Decimal("80.00"))
        self.assertEqual(self.racao.desconto_percentual, 20)

    def test_busca_filtra(self):
        resp = self.client.get(reverse("loja:busca"), {"q": "osso"})
        self.assertContains(resp, "Osso")
        self.assertNotContains(resp, "Ração")

    def test_nao_adiciona_sem_estoque(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.sem_estoque.pk]))
        self.assertEqual(self.client.session.get("carrinho", {}), {})

    def test_quantidade_limitada_ao_estoque(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.racao.pk]), {"quantidade": 99})
        self.assertEqual(self.client.session["carrinho"], {str(self.racao.pk): 5})

    def test_compra_completa_baixa_estoque(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.racao.pk]), {"quantidade": 2})
        resp = self.client.post(reverse("loja:checkout"), {
            "nome": "Ana", "email": "ana@example.com", "telefone": "",
            "cep": "01001-000", "endereco": "Rua A, 1", "cidade": "São Paulo", "uf": "sp",
        })
        pedido = Pedido.objects.get()
        self.assertRedirects(resp, reverse("loja:pedido", args=[pedido.pk]))
        self.assertEqual(pedido.uf, "SP")
        self.assertEqual(pedido.total, Decimal("160.00"))
        self.racao.refresh_from_db()
        self.assertEqual(self.racao.estoque, 3)
        self.assertFalse(self.client.session.get("carrinho"))

    def test_pedido_so_para_o_comprador(self):
        pedido = Pedido.objects.create(
            nome="Ana", email="a@e.com", cep="1", endereco="x", cidade="y", uf="SP"
        )
        resp = self.client.get(reverse("loja:pedido", args=[pedido.pk]))
        self.assertRedirects(resp, reverse("loja:home"))

    def test_checkout_com_carrinho_vazio_redireciona(self):
        resp = self.client.get(reverse("loja:checkout"))
        self.assertRedirects(resp, reverse("loja:carrinho"))
