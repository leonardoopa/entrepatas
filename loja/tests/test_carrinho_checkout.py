from decimal import Decimal

from django.test import override_settings
from django.urls import reverse

from .fabricas import DADOS_ENTREGA, BackofficeTestCase, criar_usuario

AJAX = {"X-Requested-With": "XMLHttpRequest"}


def adicionar(client, sku, quantidade=None, **extra):
    dados = {} if quantidade is None else {"quantidade": quantidade}
    return client.post(reverse("loja:carrinho_adicionar", args=[sku]), dados, **extra)


class CarrinhoViewsTests(BackofficeTestCase):
    def test_adiciona_e_guarda_so_sku_e_quantidade(self):
        adicionar(self.client, "BOL-1", 2)
        self.assertEqual(self.client.session["carrinho"], {"BOL-1": 2})

    def test_nao_adiciona_sem_estoque(self):
        resposta = adicionar(self.client, "OSS-1")
        self.assertRedirects(resposta, reverse("loja:produto", args=["oss-1"]), fetch_redirect_response=False)
        self.assertFalse(self.client.session.get("carrinho"))

    def test_limita_ao_estoque(self):
        adicionar(self.client, "RAC-1", 99)
        self.assertEqual(self.client.session["carrinho"], {"RAC-1": 5})

    def test_quantidade_invalida_vira_um(self):
        adicionar(self.client, "RAC-1", "abc")
        self.assertEqual(self.client.session["carrinho"], {"RAC-1": 1})

    def test_sku_inexistente_da_404(self):
        self.assertEqual(adicionar(self.client, "NAO-EXISTE").status_code, 404)

    def test_adicionar_via_ajax_devolve_json_com_o_minicarrinho(self):
        dados = adicionar(self.client, "BOL-1", 2, headers=AJAX).json()
        self.assertEqual((dados["ok"], dados["qtd"]), (True, 2))
        self.assertIn("Bola", dados["html"])

    def test_ajax_sem_estoque_devolve_erro(self):
        resposta = adicionar(self.client, "OSS-1", headers=AJAX)
        self.assertEqual((resposta.status_code, resposta.json()["ok"]), (400, False))

    def test_atualizar_e_remover(self):
        adicionar(self.client, "BOL-1", 2)
        self.client.post(reverse("loja:carrinho_atualizar", args=["BOL-1"]), {"quantidade": 4})
        self.assertEqual(self.client.session["carrinho"], {"BOL-1": 4})
        self.client.post(reverse("loja:carrinho_remover", args=["BOL-1"]))
        self.assertFalse(self.client.session.get("carrinho"))

    def test_resumo_com_frete_cobrado(self):
        adicionar(self.client, "BOL-1")
        resumo = self.client.get(reverse("loja:carrinho")).context["resumo"]
        self.assertEqual((resumo.frete, resumo.total, resumo.falta_para_frete_gratis), (Decimal("19.90"), Decimal("49.90"), Decimal("169.00")))

    def test_resumo_com_frete_gratis(self):
        adicionar(self.client, "RAC-G")
        resumo = self.client.get(reverse("loja:carrinho")).context["resumo"]
        self.assertEqual((resumo.frete_gratis, resumo.frete), (True, Decimal("0")))

    def test_contador_no_cabecalho(self):
        adicionar(self.client, "BOL-1", 3)
        self.assertContains(self.client.get(reverse("loja:home")), 'data-carrinho-qtd>3<')


class CheckoutViewsTests(BackofficeTestCase):
    def finalizar(self, dados=None):
        return self.client.post(reverse("loja:checkout"), dados or DADOS_ENTREGA)

    def test_compra_completa_e_pagina_de_confirmacao(self):
        adicionar(self.client, "RAC-1", 2)
        resposta = self.finalizar()
        numero = next(iter(self.bo.pedidos))
        self.assertRedirects(resposta, reverse("loja:pedido", args=[numero]), fetch_redirect_response=False)
        pedido = self.bo.pedidos[numero]
        self.assertEqual((pedido["subtotal"], pedido["frete"], pedido["total"]), ("160.00", "19.90", "179.90"))
        self.assertEqual(pedido["entrega"]["uf"], "SP")
        self.assertEqual(self.bo.produtos[0]["estoque"], 3)
        self.assertFalse(self.client.session.get("carrinho"))
        pagina = self.client.get(reverse("loja:pedido", args=[numero]))
        self.assertContains(pagina, f"Pedido {numero} recebido")
        self.assertContains(pagina, "R$ 179,90")

    def test_frete_gratis_vai_para_o_pedido(self):
        adicionar(self.client, "RAC-G")
        self.finalizar()
        self.assertEqual(next(iter(self.bo.pedidos.values()))["frete"], "0.00")

    def test_estoque_insuficiente_volta_ao_carrinho_sem_perder_itens(self):
        adicionar(self.client, "RAC-1", 5)
        self.bo.produtos[0]["estoque"] = 1
        resposta = self.client.post(reverse("loja:checkout"), DADOS_ENTREGA, follow=True)
        self.assertRedirects(resposta, reverse("loja:carrinho"), fetch_redirect_response=False)
        self.assertContains(resposta, "Estoque insuficiente para Ração")
        self.assertEqual(self.bo.pedidos, {})
        self.assertTrue(self.client.session["carrinho"])

    @override_settings(BACKOFFICE_CACHE_SEGUNDOS=30)
    def test_backoffice_fora_do_ar_mantem_carrinho_e_o_mesmo_numero_na_nova_tentativa(self):
        adicionar(self.client, "BOL-1")
        self.client.get(reverse("loja:checkout"))
        self.bo.indisponivel = True
        resposta = self.finalizar()
        self.assertEqual(resposta.status_code, 503)
        self.assertContains(resposta, "Nada foi cobrado", status_code=503)
        numero = self.client.session["checkout_numero"]
        self.assertTrue(self.client.session["carrinho"])
        self.bo.indisponivel = False
        self.finalizar()
        self.assertEqual(list(self.bo.pedidos), [numero])
        self.assertNotIn("checkout_numero", self.client.session)

    def test_pedido_recusado_pelo_backoffice(self):
        adicionar(self.client, "BOL-1")
        self.bo.falhar_pedido = (400, {"erro": "Corpo inválido"})
        resposta = self.finalizar()
        self.assertEqual(resposta.status_code, 422)
        self.assertTrue(self.client.session["carrinho"])

    def test_formulario_invalido_nao_envia_nada(self):
        adicionar(self.client, "BOL-1")
        resposta = self.finalizar({**DADOS_ENTREGA, "email": "invalido"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([c for c in self.bo.chamadas if c[0] == "POST"], [])

    def test_carrinho_vazio_redireciona(self):
        self.assertRedirects(self.client.get(reverse("loja:checkout")), reverse("loja:carrinho"))

    def test_so_o_comprador_ve_a_confirmacao(self):
        adicionar(self.client, "BOL-1")
        self.finalizar()
        numero = next(iter(self.bo.pedidos))
        outro = self.client_class()
        self.assertRedirects(outro.get(reverse("loja:pedido", args=[numero])), reverse("loja:home"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("loja:pedido", args=["NAO-EXISTE"])).status_code, 404)

    def test_usuario_logado_tem_dados_preenchidos_e_ve_o_pedido_na_conta(self):
        usuario = criar_usuario()
        self.client.force_login(usuario)
        adicionar(self.client, "BOL-1")
        self.assertEqual(self.client.get(reverse("loja:checkout")).context["form"].initial["email"], "ana@example.com")
        self.finalizar()
        pedido = next(iter(self.bo.pedidos.values()))
        self.assertEqual(pedido["cliente"]["id_externo"], str(usuario.pk))
        self.assertContains(self.client.get(reverse("loja:conta")), f"Pedido {pedido['numero_externo']}")

        outro = self.client_class()
        outro.force_login(criar_usuario("c@example.com", "Carla"))
        self.assertRedirects(outro.get(reverse("loja:pedido", args=[pedido["numero_externo"]])), reverse("loja:home"), fetch_redirect_response=False)
        self.assertNotContains(outro.get(reverse("loja:conta")), pedido["numero_externo"])

        self.client.logout()
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("loja:pedido", args=[pedido["numero_externo"]])).status_code, 200)

    def test_conta_avisa_quando_nao_consegue_carregar_pedidos(self):
        self.client.force_login(criar_usuario())
        self.bo.indisponivel = True
        resposta = self.client.get(reverse("loja:conta"))
        self.assertContains(resposta, "Não conseguimos carregar seus pedidos")
        self.assertContains(resposta, "ainda não fez nenhum pedido")
