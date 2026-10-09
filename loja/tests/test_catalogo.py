from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from .fabricas import (
    CAES, RACOES, SECA, UMIDA, BackofficeTestCase, produto_json,
)


def chamadas_de_lista(bo):
    return [c[2] for c in bo.chamadas if c[1] == "catalogo/produtos/"]


class PaginasTests(BackofficeTestCase):
    def test_paginas_publicas(self):
        for url in [
            reverse("loja:home"), reverse("loja:ofertas"), reverse("loja:categoria", args=["caes"]),
            reverse("loja:departamento", args=["racoes"]), reverse("loja:produto", args=["rac-1"]),
            reverse("loja:busca") + "?q=ra", reverse("loja:carrinho"), reverse("loja:minicarrinho"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_animal_departamento_e_produto_desconhecidos_dao_404(self):
        for url in (
            reverse("loja:categoria", args=["dragoes"]), reverse("loja:departamento", args=["magia"]),
            reverse("loja:produto", args=["nao-existe"]),
        ):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_pagina_do_produto_mostra_preco_promocional_e_desconto(self):
        html = self.client.get(reverse("loja:produto", args=["rac-1"])).content.decode()
        self.assertIn("-20%", html)
        self.assertIn("R$ 80,00", html)
        self.assertIn("R$ 100,00", html)

    def test_produto_sem_estoque_mostra_indisponivel(self):
        self.assertContains(self.client.get(reverse("loja:produto", args=["oss-1"])), "indisponível")


class ListagemTests(BackofficeTestCase):
    def slugs(self, resposta):
        return [p.sku for p in resposta.context["pagina"]]

    def test_animal_vira_escopo_na_chamada_da_api(self):
        resposta = self.client.get(reverse("loja:categoria", args=["gatos"]))
        self.assertEqual(self.slugs(resposta), ["RAC-G"])
        self.assertIn(("escopo_animal", "gatos"), chamadas_de_lista(self.bo)[-1])

    def test_filtros_viram_parametros(self):
        self.client.get(reverse("loja:busca"), {"depto": "racoes", "sub": "racao-seca", "marca": "nutripet", "faixa": "50-100", "promo": "1", "ordem": "menor-preco"})
        parametros = dict(chamadas_de_lista(self.bo)[-1])
        self.assertEqual(
            parametros,
            {"departamento": "racoes", "subdepartamento": "racao-seca", "marca": "nutripet", "faixa": "50-100", "promo": "1",
             "ordem": "menor-preco", "pagina": "1", "tamanho": "12"},
        )

    def test_valores_invalidos_sao_descartados(self):
        self.client.get(reverse("loja:busca"), {"faixa": "barata", "ordem": "aleatoria"})
        parametros = dict(chamadas_de_lista(self.bo)[-1])
        self.assertNotIn("faixa", parametros)
        self.assertEqual(parametros["ordem"], "relevancia")

    def test_busca_por_termo(self):
        resposta = self.client.get(reverse("loja:busca"), {"q": "osso"})
        self.assertEqual(self.slugs(resposta), ["OSS-1"])
        self.assertContains(resposta, "Resultados para “osso”")

    def test_busca_sem_resultado_e_registrada(self):
        with self.assertLogs("loja.views.catalogo", "INFO") as logs:
            resposta = self.client.get(reverse("loja:busca"), {"q": "unicornio"})
        self.assertContains(resposta, "Nenhum produto encontrado")
        self.assertIn("busca_sem_resultado", logs.output[0])

    def test_ofertas(self):
        self.assertEqual(self.slugs(self.client.get(reverse("loja:ofertas"))), ["RAC-1"])

    def test_filtros_ativos_aparecem_na_pagina(self):
        self.bo.produtos.append(produto_json("RAC-2", "Ração Úmida", CAES, "20.00", None, 5, RACOES, UMIDA, "NutriPet"))
        resposta = self.client.get(reverse("loja:categoria", args=["caes"]), {"depto": "racoes"})
        self.assertTrue(resposta.context["filtros"].ativos)
        self.assertContains(resposta, "Limpar filtros")
        self.assertContains(resposta, 'value="racao-seca"')

    def test_facetas_de_marca_usam_o_slug(self):
        html = self.client.get(reverse("loja:categoria", args=["caes"])).content.decode()
        self.assertIn('name="marca" value="nutripet"', html)
        self.assertIn("NutriPet", html)


class PaginacaoTests(BackofficeTestCase):
    @staticmethod
    def produtos_iniciais():
        return [produto_json(f"P-{i:02d}", f"Produto {i:02d}", CAES, "10.00") for i in range(30)]

    def test_tres_paginas_e_links_preservam_filtros(self):
        resposta = self.client.get(reverse("loja:busca"), {"ordem": "nome", "pagina": 2})
        pagina = resposta.context["pagina"]
        self.assertEqual((pagina.numero, pagina.total_paginas, len(pagina)), (2, 3, 12))
        html = resposta.content.decode()
        self.assertIn("ordem=nome&amp;pagina=1", html)
        self.assertIn("ordem=nome&amp;pagina=3", html)
        self.assertIn('aria-current="page"', html)

    def test_pagina_invalida_volta_para_a_primeira(self):
        self.assertEqual(self.client.get(reverse("loja:busca"), {"pagina": "abc"}).context["pagina"].numero, 1)
        self.assertEqual(self.client.get(reverse("loja:busca"), {"pagina": "-4"}).context["pagina"].numero, 1)


class SugestoesTests(BackofficeTestCase):
    def test_devolve_nome_preco_url_e_arte(self):
        itens = self.client.get(reverse("loja:sugestoes"), {"q": "ração"}).json()["itens"]
        self.assertEqual({i["nome"] for i in itens}, {"Ração", "Ração Gato"})
        racao = next(i for i in itens if i["nome"] == "Ração")
        self.assertEqual((racao["preco"], racao["url"], racao["marca"]), ("80,00", "/produto/rac-1/", "NutriPet"))
        self.assertIn("<svg", racao["arte"])

    def test_termo_curto_nao_consulta(self):
        self.assertEqual(self.client.get(reverse("loja:sugestoes"), {"q": "r"}).json(), {"itens": []})
        self.assertEqual(self.bo.chamadas, [])


class VariacoesTests(BackofficeTestCase):
    @staticmethod
    def produtos_iniciais():
        return [
            produto_json("RAC-15", "Ração 15kg", CAES, "150.00", None, 5, RACOES, SECA, "NutriPet", grupo="Ração", variacao="15 kg"),
            produto_json("RAC-3", "Ração 3kg", CAES, "40.00", None, 7, RACOES, SECA, "NutriPet", grupo="Ração", variacao="3 kg"),
            produto_json("RAC-30", "Ração 30kg", CAES, "300.00", None, 0, RACOES, SECA, "NutriPet", grupo="Ração", variacao="30 kg"),
        ]

    def test_chips_de_variacao_em_ordem_de_preco_com_a_atual_marcada(self):
        html = self.client.get(reverse("loja:produto", args=["rac-15"])).content.decode()
        self.assertLess(html.index("3 kg"), html.index("15 kg"))
        self.assertEqual(html.count("variacao--ativa"), 1)
        self.assertIn("variacao--esgotada", html)
        self.assertIn('href="/produto/rac-3/"', html)

    def test_produto_sem_grupo_nao_mostra_chips(self):
        self.bo.produtos[0]["grupo"] = None
        self.assertNotContains(self.client.get(reverse("loja:produto", args=["rac-15"])), 'class="variacoes"')


class ProdutoPaginaTests(BackofficeTestCase):
    def test_relacionados_nao_incluem_o_proprio_produto(self):
        relacionados = self.client.get(reverse("loja:produto", args=["rac-1"])).context["relacionados"]
        self.assertNotIn("RAC-1", [p.sku for p in relacionados])

    def test_imagens_reais_substituem_o_desenho(self):
        self.bo.produtos[0]["imagens"] = ["https://cdn.exemplo.com/foto.jpg"]
        html = self.client.get(reverse("loja:produto", args=["rac-1"])).content.decode()
        self.assertIn('<img src="https://cdn.exemplo.com/foto.jpg"', html)

    def test_marca_leva_para_a_busca_pelo_slug(self):
        self.assertContains(self.client.get(reverse("loja:produto", args=["rac-1"])), "?marca=nutripet")


class HomeTests(BackofficeTestCase):
    def test_mostra_as_vitrines_com_o_nome_do_backoffice(self):
        self.bo.vitrines_json = {
            "ofertas": {"nome": "Semana do Pet", "itens": [self.bo.produtos[0]]},
            "mais_vendidos": {"nome": "Queridinhos", "itens": [self.bo.produtos[1]]},
            "destaques": {"nome": "Escolhas da casa", "itens": [self.bo.produtos[2]]},
        }
        html = self.client.get(reverse("loja:home")).content.decode()
        for nome in ("Semana do Pet", "Queridinhos", "Escolhas da casa"):
            self.assertIn(nome, html)

    def test_vitrine_vazia_nao_aparece(self):
        self.bo.vitrines_json = {
            "ofertas": {"nome": "Ofertas X", "itens": []}, "mais_vendidos": {"nome": "Vendidos X", "itens": []},
            "destaques": {"nome": "Destaques X", "itens": []},
        }
        html = self.client.get(reverse("loja:home")).content.decode()
        self.assertNotIn("Ofertas X", html)
        self.assertNotIn("Destaques X", html)

    def test_menu_vem_da_taxonomia_do_backoffice(self):
        self.bo.produtos.append(produto_json("RAC-2", "Ração Úmida", CAES, "20.00", None, 5, RACOES, UMIDA, "NutriPet"))
        html = self.client.get(reverse("loja:home")).content.decode()
        self.assertIn('data-animal="caes"', html)
        self.assertIn("mega__sub", html)

    def test_marcas_favoritas_vem_das_facetas(self):
        self.assertContains(self.client.get(reverse("loja:home")), "?marca=patafeliz")


class ResilienciaTests(BackofficeTestCase):
    def test_sem_backoffice_e_sem_cache_mostra_pagina_de_manutencao(self):
        self.bo.indisponivel = True
        resposta = self.client.get(reverse("loja:busca"))
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta["Retry-After"], "30")
        self.assertContains(resposta, "Estamos ajeitando a loja", status_code=503)

    def test_menu_vazio_nao_derruba_as_paginas_estaticas(self):
        self.bo.indisponivel = True
        self.assertEqual(self.client.get(reverse("loja:entrar")).status_code, 200)

    @override_settings(BACKOFFICE_CACHE_SEGUNDOS=30)
    def test_pagina_ja_vista_continua_no_ar_com_o_backoffice_fora(self):
        cache.clear()
        self.assertEqual(self.client.get(reverse("loja:categoria", args=["caes"])).status_code, 200)
        cache.delete_many([k for k in cache._cache if k.startswith(":1:bo:")])
        self.bo.indisponivel = True
        self.assertEqual(self.client.get(reverse("loja:categoria", args=["caes"])).status_code, 200)

    def test_erro_de_outro_tipo_nao_vira_pagina_de_manutencao(self):
        self.bo.get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bug"))
        with self.assertRaises(RuntimeError):
            self.client.get(reverse("loja:busca"))
