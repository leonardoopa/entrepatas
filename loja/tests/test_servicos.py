from decimal import Decimal

from django.test import TestCase

from loja.models import Pedido
from loja.services.carrinho import Carrinho, ProdutoSemEstoque
from loja.services.checkout import CarrinhoVazio, ItemIndisponivel, finalizar_pedido
from loja.services.frete import FreteFixoComMinimoGratis
from loja.services.resumo import montar_resumo
from loja.texto import normalizar

from .fabricas import DADOS_ENTREGA, criar_catalogo, criar_usuario

POLITICA = FreteFixoComMinimoGratis(valor_fixo=Decimal("10.00"), valor_para_frete_gratis=Decimal("100.00"))


class PoliticaFreteTests(TestCase):
    def test_cobra_frete_abaixo_do_minimo(self):
        self.assertEqual(POLITICA.calcular(Decimal("99.99")), Decimal("10.00"))

    def test_gratis_a_partir_do_minimo(self):
        self.assertEqual(POLITICA.calcular(Decimal("100.00")), Decimal("0"))


class ResumoCompraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c = criar_catalogo()

    def linhas(self, *itens):
        carrinho = Carrinho({})
        for produto, quantidade in itens:
            carrinho.adicionar(produto, quantidade)
        return carrinho.linhas()

    def test_carrinho_vazio_nao_cobra_frete(self):
        resumo = montar_resumo([], POLITICA)
        self.assertEqual((resumo.subtotal, resumo.frete, resumo.total), (Decimal("0"), Decimal("0"), Decimal("0")))

    def test_totais_e_progresso(self):
        resumo = montar_resumo(self.linhas((self.c["bola"], 2)), POLITICA)
        self.assertEqual(resumo.subtotal, Decimal("60.00"))
        self.assertEqual(resumo.total, Decimal("70.00"))
        self.assertEqual(resumo.falta_para_frete_gratis, Decimal("40.00"))
        self.assertEqual(resumo.progresso_frete, 60)
        self.assertFalse(resumo.frete_gratis)

    def test_frete_gratis_zera_o_frete(self):
        resumo = montar_resumo(self.linhas((self.c["racao_gato"], 1)), POLITICA)
        self.assertTrue(resumo.frete_gratis)
        self.assertEqual(resumo.frete, Decimal("0"))
        self.assertEqual(resumo.progresso_frete, 100)


class CarrinhoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c = criar_catalogo()

    def test_adicionar_soma_quantidades(self):
        carrinho = Carrinho({})
        carrinho.adicionar(self.c["bola"], 2)
        carrinho.adicionar(self.c["bola"], 3)
        self.assertEqual(carrinho.itens, {self.c["bola"].pk: 5})
        self.assertEqual(len(carrinho), 5)

    def test_limita_ao_estoque(self):
        carrinho = Carrinho({})
        carrinho.adicionar(self.c["racao"], 99)
        self.assertEqual(carrinho.itens, {self.c["racao"].pk: 5})

    def test_produto_sem_estoque_levanta_erro(self):
        with self.assertRaises(ProdutoSemEstoque):
            Carrinho({}).adicionar(self.c["osso"])

    def test_quantidade_zero_remove(self):
        carrinho = Carrinho({})
        carrinho.adicionar(self.c["bola"])
        carrinho.definir(self.c["bola"], 0)
        self.assertEqual(carrinho.itens, {})

    def test_linhas_ignoram_produtos_inativos(self):
        carrinho = Carrinho({})
        carrinho.adicionar(self.c["bola"])
        self.c["bola"].ativo = False
        self.c["bola"].save()
        self.assertEqual(carrinho.linhas(), [])

    def test_guarda_na_sessao_com_chaves_de_texto(self):
        sessao = {}
        Carrinho(sessao).adicionar(self.c["bola"])
        self.assertEqual(sessao["carrinho"], {str(self.c["bola"].pk): 1})


class FinalizarPedidoTests(TestCase):
    def setUp(self):
        self.c = criar_catalogo()
        self.dados = {**DADOS_ENTREGA, "uf": "SP"}

    def test_cria_pedido_itens_e_baixa_estoque(self):
        usuario = criar_usuario()
        pedido = finalizar_pedido(
            dados_entrega=self.dados, itens={self.c["racao"].pk: 2}, usuario=usuario, politica_frete=POLITICA,
        )
        self.assertEqual(pedido.usuario, usuario)
        self.assertEqual(pedido.subtotal, Decimal("160.00"))
        self.assertEqual(pedido.frete, Decimal("0"))
        self.assertEqual(pedido.itens.get().preco_unitario, Decimal("80.00"))
        self.c["racao"].refresh_from_db()
        self.assertEqual((self.c["racao"].estoque, self.c["racao"].vendas), (3, 12))

    def test_cobra_frete_pela_politica(self):
        pedido = finalizar_pedido(dados_entrega=self.dados, itens={self.c["bola"].pk: 1}, politica_frete=POLITICA)
        self.assertEqual(pedido.frete, Decimal("10.00"))
        self.assertIsNone(pedido.usuario)

    def test_carrinho_vazio(self):
        with self.assertRaises(CarrinhoVazio):
            finalizar_pedido(dados_entrega=self.dados, itens={})

    def test_estoque_insuficiente_nao_grava_nada(self):
        itens = {self.c["bola"].pk: 1, self.c["racao"].pk: 6}
        with self.assertRaises(ItemIndisponivel) as contexto:
            finalizar_pedido(dados_entrega=self.dados, itens=itens, politica_frete=POLITICA)
        self.assertEqual(contexto.exception.nome, "Ração")
        self.assertEqual(Pedido.objects.count(), 0)
        self.c["bola"].refresh_from_db()
        self.assertEqual(self.c["bola"].estoque, 50)

    def test_produto_inativo_e_indisponivel(self):
        self.c["bola"].ativo = False
        self.c["bola"].save()
        with self.assertRaises(ItemIndisponivel):
            finalizar_pedido(dados_entrega=self.dados, itens={self.c["bola"].pk: 1})


class TextoTests(TestCase):
    def test_normalizar_remove_acentos_e_espacos_extras(self):
        self.assertEqual(normalizar("  Ração  PREMIUM — Cães "), "racao premium caes")
