from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from loja.backoffice.catalogo import CatalogoBackoffice
from loja.backoffice.pedidos import PedidosBackoffice
from loja.erros import CarrinhoVazio, CheckoutIndisponivel, ItemIndisponivel
from loja.services.carrinho import Carrinho, ProdutoSemEstoque
from loja.services.checkout import finalizar_pedido, novo_numero_pedido
from loja.services.frete import FreteFixoComMinimoGratis
from loja.services.resumo import montar_resumo

from .fabricas import BackofficeFalso, DADOS_ENTREGA

POLITICA = FreteFixoComMinimoGratis(valor_fixo=Decimal("10.00"), valor_para_frete_gratis=Decimal("100.00"))


class _ComBackoffice(SimpleTestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.bo = BackofficeFalso()
        self.catalogo = CatalogoBackoffice(self.bo, cache, ttl=0)
        self.produto = lambda sku: self.catalogo.produtos_por_sku([sku])[0]

    def carrinho(self, sessao=None):
        return Carrinho({} if sessao is None else sessao, self.catalogo)


class PoliticaFreteTests(SimpleTestCase):
    def test_cobra_frete_abaixo_do_minimo(self):
        self.assertEqual(POLITICA.calcular(Decimal("99.99")), Decimal("10.00"))

    def test_gratis_a_partir_do_minimo(self):
        self.assertEqual(POLITICA.calcular(Decimal("100.00")), Decimal("0"))


class ResumoCompraTests(_ComBackoffice):
    def linhas(self, *itens):
        carrinho = self.carrinho()
        for sku, quantidade in itens:
            carrinho.adicionar(self.produto(sku), quantidade)
        return carrinho.linhas()

    def test_carrinho_vazio_nao_cobra_frete(self):
        resumo = montar_resumo([], POLITICA)
        self.assertEqual((resumo.subtotal, resumo.frete, resumo.total), (Decimal("0"), Decimal("0"), Decimal("0")))

    def test_totais_e_progresso(self):
        resumo = montar_resumo(self.linhas(("BOL-1", 2)), POLITICA)
        self.assertEqual((resumo.subtotal, resumo.total), (Decimal("60.00"), Decimal("70.00")))
        self.assertEqual((resumo.falta_para_frete_gratis, resumo.progresso_frete, resumo.frete_gratis), (Decimal("40.00"), 60, False))

    def test_frete_gratis_zera_o_frete(self):
        resumo = montar_resumo(self.linhas(("RAC-G", 1)), POLITICA)
        self.assertEqual((resumo.frete_gratis, resumo.frete, resumo.progresso_frete), (True, Decimal("0"), 100))


class CarrinhoTests(_ComBackoffice):
    def test_adicionar_soma_quantidades(self):
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("BOL-1"), 2)
        carrinho.adicionar(self.produto("BOL-1"), 3)
        self.assertEqual((carrinho.itens, len(carrinho)), ({"BOL-1": 5}, 5))

    def test_limita_ao_estoque(self):
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("RAC-1"), 99)
        self.assertEqual(carrinho.itens, {"RAC-1": 5})

    def test_produto_sem_estoque_levanta_erro(self):
        with self.assertRaises(ProdutoSemEstoque):
            self.carrinho().adicionar(self.produto("OSS-1"))

    def test_quantidade_zero_remove(self):
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("BOL-1"))
        carrinho.definir(self.produto("BOL-1"), 0)
        self.assertEqual(carrinho.itens, {})

    def test_remover_e_limpar(self):
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("BOL-1"))
        carrinho.adicionar(self.produto("RAC-1"))
        carrinho.remover("BOL-1")
        self.assertEqual(carrinho.itens, {"RAC-1": 1})
        carrinho.limpar()
        self.assertEqual(carrinho.itens, {})

    def test_linhas_ignoram_produto_que_saiu_do_catalogo(self):
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("BOL-1"))
        carrinho.adicionar(self.produto("RAC-1"))
        self.bo.produtos = [p for p in self.bo.produtos if p["sku"] != "BOL-1"]
        self.assertEqual([l.produto.sku for l in carrinho.linhas()], ["RAC-1"])

    def test_linhas_usam_o_preco_atual_do_catalogo(self):
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("BOL-1"), 2)
        self.bo.produtos[1]["preco_final"] = "25.00"
        self.assertEqual(carrinho.linhas()[0].subtotal, Decimal("50.00"))

    def test_guarda_na_sessao_so_sku_e_quantidade(self):
        sessao = {}
        self.carrinho(sessao).adicionar(self.produto("BOL-1"))
        self.assertEqual(sessao["carrinho"], {"BOL-1": 1})


class FinalizarPedidoTests(_ComBackoffice):
    def setUp(self):
        super().setUp()
        self.pedidos = PedidosBackoffice(self.bo)
        carrinho = self.carrinho()
        carrinho.adicionar(self.produto("BOL-1"), 2)
        self.linhas = carrinho.linhas()
        self.resumo = montar_resumo(self.linhas, POLITICA)

    def finalizar(self, numero="S-1", usuario=None, linhas=None):
        return finalizar_pedido(
            numero=numero, dados_entrega=DADOS_ENTREGA | {"uf": "SP"}, linhas=self.linhas if linhas is None else linhas,
            resumo=self.resumo, pedidos=self.pedidos, usuario=usuario,
        )

    def test_envia_itens_frete_e_entrega(self):
        criado = self.finalizar()
        corpo = self.bo.chamadas[-1][2]
        self.assertEqual(corpo["itens"], [{"sku": "BOL-1", "quantidade": 2}])
        self.assertEqual((corpo["frete"], corpo["entrega"]["uf"]), ("10.00", "SP"))
        self.assertEqual((criado.numero, criado.total), ("S-1", Decimal("70.00")))

    def test_visitante_e_identificado_pelo_email(self):
        self.finalizar()
        self.assertEqual(self.bo.chamadas[-1][2]["cliente"]["id_externo"], "visitante:ana@example.com")

    def test_usuario_logado_e_identificado_pelo_id(self):
        usuario = get_user_model()(pk=42, email="ana@example.com", first_name="Ana")
        self.finalizar(usuario=usuario)
        self.assertEqual(self.bo.chamadas[-1][2]["cliente"], {"id_externo": "42", "nome": "Ana", "email": "ana@example.com"})

    def test_carrinho_vazio(self):
        with self.assertRaises(CarrinhoVazio):
            self.finalizar(linhas=[])

    def test_estoque_insuficiente_traz_o_nome_do_produto(self):
        self.bo.produtos[1]["estoque"] = 1
        with self.assertRaises(ItemIndisponivel) as contexto:
            self.finalizar()
        self.assertEqual((contexto.exception.sku, contexto.exception.nome), ("BOL-1", "Bola"))

    def test_backoffice_fora_do_ar(self):
        self.bo.indisponivel = True
        with self.assertRaises(CheckoutIndisponivel):
            self.finalizar()

    def test_reenviar_o_mesmo_numero_nao_duplica(self):
        self.finalizar()
        repetido = self.finalizar()
        self.assertFalse(repetido.criado)
        self.assertEqual(len(self.bo.pedidos), 1)
        self.assertEqual(self.bo.produtos[1]["estoque"], 48)

    def test_numero_do_pedido_tem_formato_e_nao_repete(self):
        numeros = {novo_numero_pedido() for _ in range(50)}
        self.assertEqual(len(numeros), 50)
        self.assertRegex(next(iter(numeros)), r"^S\d{6}-[0-9A-F]{6}$")
