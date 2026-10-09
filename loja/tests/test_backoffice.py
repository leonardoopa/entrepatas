import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import requests
from django.core.cache import caches
from django.test import SimpleTestCase, TestCase

from loja.backoffice import mapeamento
from loja.backoffice.catalogo import CatalogoBackoffice
from loja.backoffice.cliente import ClienteBackoffice
from loja.backoffice.erros import BackofficeIndisponivel, BackofficeNaoEncontrado, BackofficeRecusou
from loja.backoffice.pedidos import PedidosBackoffice
from loja.dominio import NovoPedido
from loja.erros import CheckoutIndisponivel, ItemIndisponivel, PedidoRecusado

from .fabricas import BackofficeFalso

CONTRATO = Path(__file__).parent / "contrato"


def carregar(nome):
    return json.loads((CONTRATO / f"{nome}.json").read_text())


class ContratoComAApiRealTests(SimpleTestCase):
    """As respostas em tests/contrato foram capturadas da API real do backoffice. Se o formato mudar, estes testes quebram."""

    def test_taxonomia(self):
        menu = mapeamento.menu(carregar("taxonomia"))
        caes = next(i for i in menu if i.categoria.slug == "caes")
        racoes = next(e for e in caes.departamentos if e.departamento.slug == "racoes")
        self.assertEqual(caes.categoria.nome, "Cães")
        self.assertTrue(any(s.slug == "racao-seca" for s in racoes.subdepartamentos))

    def test_lista_de_produtos(self):
        pagina = mapeamento.pagina(carregar("lista"))
        self.assertEqual((pagina.numero, len(pagina.itens) <= pagina.total), (1, True))
        produto = pagina.itens[0]
        self.assertIsInstance(produto.preco_final, Decimal)
        self.assertTrue(produto.sku and produto.slug and produto.categoria.slug)

    def test_facetas(self):
        facetas = mapeamento.facetas(carregar("lista")["facetas"])
        self.assertTrue(facetas.animais and facetas.marcas)

    def test_detalhe_com_variacoes_e_grupo(self):
        produto = mapeamento.produto(carregar("detalhe"))
        self.assertTrue(produto.grupo)
        self.assertGreaterEqual(len(produto.variacoes), 2)
        self.assertIn(produto.sku, {v.sku for v in produto.variacoes})

    def test_vitrines(self):
        vitrines = mapeamento.vitrines(carregar("vitrines"))
        self.assertEqual(set(vitrines), {"ofertas", "mais_vendidos", "destaques"})
        self.assertTrue(all(p.preco_final > 0 for p in vitrines["ofertas"].itens))


class MapeamentoTests(SimpleTestCase):
    def test_produto_sem_campos_opcionais(self):
        bruto = {
            "sku": "A", "slug": "a", "nome": "A", "animal": {"slug": "caes", "nome": "Cães"}, "preco": "10.00",
            "preco_final": "10.00",
        }
        produto = mapeamento.produto(bruto)
        self.assertEqual((produto.marca, produto.departamento, produto.imagens, produto.estoque, produto.em_promocao), ("", None, (), 0, False))

    def test_promocao_e_calculos(self):
        bruto = {
            "sku": "A", "slug": "a", "nome": "A", "animal": {"slug": "caes", "nome": "Cães"}, "preco": "100.00",
            "preco_promocional": "80.00", "preco_final": "80.00", "avaliacao": "4.5", "promocao_fim": "2026-10-20T23:59:00+00:00",
        }
        produto = mapeamento.produto(bruto)
        self.assertEqual((produto.em_promocao, produto.desconto_percentual, produto.avaliacao_pct), (True, 20, 90))
        self.assertEqual(produto.parcelas, (3, Decimal("26.67")))
        self.assertEqual(produto.promocao_fim.day, 20)

    def test_pedido(self):
        pedido = mapeamento.pedido({
            "numero_externo": "S-1", "status": "pago", "subtotal": "60.00", "frete": "10.00", "total": "70.00",
            "comprado_em": "2026-10-09T15:00:00+00:00", "cliente": {"id_externo": "7", "nome": "Ana", "email": "a@e.com"},
            "entrega": {"cidade": "SP", "uf": "SP"}, "itens": [{"sku": "A", "descricao": "Bola", "quantidade": 2, "preco_unitario": "30.00"}],
        })
        self.assertEqual((pedido.status_rotulo, pedido.cliente_id, pedido.cidade, pedido.itens[0].subtotal), ("Pago", "7", "SP", Decimal("60.00")))


class ClienteHttpTests(SimpleTestCase):
    def cliente(self, resposta=None, erro=None):
        sessao = MagicMock(spec=requests.Session)
        sessao.headers = {}
        if erro:
            sessao.request.side_effect = erro
        else:
            sessao.request.return_value = resposta
        return ClienteBackoffice("http://bo/api/v1/", "chave-secreta", timeout=3, sessao=sessao), sessao

    @staticmethod
    def resposta(status, corpo=None):
        r = MagicMock(spec=requests.Response)
        r.status_code = status
        r.json.return_value = corpo if corpo is not None else {}
        return r

    def test_envia_chave_url_e_timeout(self):
        cliente, sessao = self.cliente(self.resposta(200, {"ok": 1}))
        self.assertEqual(cliente.get("/vitrines/", [("a", "1")]), {"ok": 1})
        sessao.request.assert_called_once_with("GET", "http://bo/api/v1/vitrines/", timeout=3, params=[("a", "1")])
        self.assertEqual(sessao.headers["Authorization"], "Bearer chave-secreta")

    def test_erros_de_rede_e_5xx_viram_indisponivel(self):
        with self.assertRaises(BackofficeIndisponivel):
            self.cliente(erro=requests.ConnectionError("x"))[0].get("a/")
        with self.assertRaises(BackofficeIndisponivel):
            self.cliente(erro=requests.Timeout("x"))[0].get("a/")
        with self.assertRaises(BackofficeIndisponivel):
            self.cliente(self.resposta(503))[0].get("a/")

    def test_404_e_4xx(self):
        with self.assertRaises(BackofficeNaoEncontrado):
            self.cliente(self.resposta(404))[0].get("a/")
        with self.assertRaises(BackofficeRecusou) as contexto:
            self.cliente(self.resposta(409, {"erro": "x", "sku": "A"}))[0].post("pedidos/", {})
        self.assertEqual((contexto.exception.status, contexto.exception.dados["sku"]), (409, "A"))

    def test_post_devolve_status_e_corpo(self):
        cliente, _ = self.cliente(self.resposta(201, {"id": 1}))
        self.assertEqual(cliente.post("pedidos/", {"a": 1}), (201, {"id": 1}))

    def test_resposta_sem_json_nao_quebra(self):
        resposta = self.resposta(200)
        resposta.json.side_effect = ValueError
        self.assertEqual(self.cliente(resposta)[0].get("a/"), {})

    def test_nenhum_log_expoe_a_chave(self):
        with self.assertLogs("loja.backoffice.cliente", "WARNING") as logs:
            with self.assertRaises(BackofficeIndisponivel):
                self.cliente(erro=requests.ConnectionError("x"))[0].get("a/")
        self.assertNotIn("chave-secreta", "\n".join(logs.output))


class CatalogoComCacheTests(TestCase):
    def setUp(self):
        self.cache = caches["default"]
        self.cache.clear()
        self.addCleanup(self.cache.clear)
        self.bo = BackofficeFalso()
        self.catalogo = CatalogoBackoffice(self.bo, self.cache, ttl=30)

    def consultas(self):
        return [c for c in self.bo.chamadas if c[1] == "vitrines/"]

    def test_segunda_leitura_vem_do_cache(self):
        self.catalogo.vitrines()
        self.catalogo.vitrines()
        self.assertEqual(len(self.consultas()), 1)

    def test_ttl_zero_desliga_o_cache(self):
        sem_cache = CatalogoBackoffice(self.bo, self.cache, ttl=0)
        sem_cache.vitrines()
        sem_cache.vitrines()
        self.assertEqual(len(self.consultas()), 2)

    def test_parametros_diferentes_geram_chaves_diferentes(self):
        self.catalogo.listar([("q", "a")], 1, 12)
        self.catalogo.listar([("q", "b")], 1, 12)
        self.catalogo.listar([("q", "a")], 1, 12)
        self.assertEqual(len([c for c in self.bo.chamadas if c[1] == "catalogo/produtos/"]), 2)

    def test_ordem_dos_parametros_nao_muda_a_chave(self):
        self.catalogo.listar([("q", "a"), ("faixa", "50-100")], 1, 12)
        self.catalogo.listar([("faixa", "50-100"), ("q", "a")], 1, 12)
        self.assertEqual(len([c for c in self.bo.chamadas if c[1] == "catalogo/produtos/"]), 1)

    def test_fora_do_ar_serve_a_ultima_copia(self):
        esperado = self.catalogo.vitrines()
        self.cache.delete_many([k for k in ("bo:" + self.catalogo._chave("vitrines/", None),)])
        self.bo.indisponivel = True
        self.assertEqual(self.catalogo.vitrines(), esperado)

    def test_fora_do_ar_sem_copia_propaga_o_erro(self):
        self.bo.indisponivel = True
        with self.assertRaises(BackofficeIndisponivel):
            self.catalogo.vitrines()

    def test_produto_inexistente_devolve_none_e_nao_vai_para_o_cache(self):
        self.assertIsNone(self.catalogo.produto("nao-existe"))
        self.assertIsNone(self.catalogo.produto("nao-existe"))
        self.assertEqual(len([c for c in self.bo.chamadas if "nao-existe" in c[1]]), 2)

    def test_produtos_por_sku_sem_skus_nao_consulta(self):
        self.assertEqual(self.catalogo.produtos_por_sku([]), [])
        self.assertEqual(self.bo.chamadas, [])

    def test_produtos_por_sku(self):
        self.assertEqual({p.sku for p in self.catalogo.produtos_por_sku(["RAC-1", "BOL-1", "NAO"])}, {"RAC-1", "BOL-1"})


class PedidosBackofficeTests(TestCase):
    def setUp(self):
        self.bo = BackofficeFalso()
        self.pedidos = PedidosBackoffice(self.bo)
        self.novo = NovoPedido(
            numero="S-1", itens=(("BOL-1", 2),), cliente={"id_externo": "7", "nome": "Ana"}, entrega={"cidade": "SP"}, frete=Decimal("19.90"),
        )

    def test_envia_o_corpo_esperado(self):
        criado = self.pedidos.criar(self.novo)
        _, caminho, corpo = self.bo.chamadas[-1]
        self.assertEqual(caminho, "pedidos/")
        self.assertEqual(corpo["itens"], [{"sku": "BOL-1", "quantidade": 2}])
        self.assertEqual((corpo["frete"], corpo["numero_externo"]), ("19.90", "S-1"))
        self.assertEqual((criado.numero, criado.total, criado.criado), ("S-1", Decimal("79.90"), True))

    def test_pedido_repetido_nao_e_novo(self):
        self.pedidos.criar(self.novo)
        self.assertFalse(self.pedidos.criar(self.novo).criado)

    def test_estoque_insuficiente_vira_item_indisponivel(self):
        with self.assertRaises(ItemIndisponivel) as contexto:
            self.pedidos.criar(NovoPedido("S-2", (("RAC-1", 99),), {}, {}, Decimal("0")))
        self.assertEqual(contexto.exception.sku, "RAC-1")

    def test_sku_inexistente_vira_item_indisponivel(self):
        with self.assertRaises(ItemIndisponivel):
            self.pedidos.criar(NovoPedido("S-3", (("NAO",  1),), {}, {}, Decimal("0")))

    def test_recusa_sem_sku_vira_pedido_recusado(self):
        self.bo.falhar_pedido = (400, {"erro": "Corpo inválido"})
        with self.assertRaises(PedidoRecusado):
            self.pedidos.criar(self.novo)

    def test_backoffice_fora_vira_checkout_indisponivel(self):
        self.bo.indisponivel = True
        with self.assertRaises(CheckoutIndisponivel):
            self.pedidos.criar(self.novo)

    def test_obter_e_listar(self):
        self.pedidos.criar(self.novo)
        self.assertEqual(self.pedidos.obter("S-1").cliente_id, "7")
        self.assertIsNone(self.pedidos.obter("NAO"))
        self.assertEqual([p.numero for p in self.pedidos.do_cliente("7")], ["S-1"])
        self.assertEqual(self.pedidos.do_cliente("outro"), [])
