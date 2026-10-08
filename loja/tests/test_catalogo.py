from decimal import Decimal

from django.core.management import call_command
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from loja.models import Produto
from loja.selectors.catalogo import FiltrosListagem

from .fabricas import criar_catalogo


class FiltrosListagemTests(TestCase):
    def test_le_parametros_validos(self):
        filtros = FiltrosListagem.de_querydict(
            QueryDict("depto=racoes&depto=petiscos&animal=caes&marca=X&faixa=50-100&promo=1&ordem=menor-preco")
        )
        self.assertEqual(filtros.departamentos, ("racoes", "petiscos"))
        self.assertEqual((filtros.animais, filtros.marcas), (("caes",), ("X",)))
        self.assertEqual((filtros.faixa, filtros.ordem), ("50-100", "menor-preco"))
        self.assertTrue(filtros.somente_ofertas)
        self.assertTrue(filtros.ativos)

    def test_ignora_valores_invalidos(self):
        filtros = FiltrosListagem.de_querydict(QueryDict("faixa=barata&ordem=aleatoria"))
        self.assertEqual((filtros.faixa, filtros.ordem), ("", "relevancia"))
        self.assertFalse(filtros.ativos)


class CatalogoViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c = criar_catalogo()

    def slugs(self, resposta):
        return [produto.slug for produto in resposta.context["pagina"]]

    def test_paginas_publicas(self):
        urls = [
            reverse("loja:home"),
            reverse("loja:ofertas"),
            self.c["caes"].get_absolute_url(),
            self.c["racoes"].get_absolute_url(),
            self.c["racao"].get_absolute_url(),
            reverse("loja:busca") + "?q=ra",
            reverse("loja:carrinho"),
            reverse("loja:minicarrinho"),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_preco_promocional_e_parcelas(self):
        racao = self.c["racao"]
        self.assertEqual(racao.preco_final, Decimal("80.00"))
        self.assertEqual(racao.desconto_percentual, 20)
        self.assertEqual(racao.parcelas, (3, Decimal("26.67")))
        self.assertEqual(self.c["osso"].parcelas, (1, Decimal("10.00")))

    def test_busca_por_termo(self):
        resposta = self.client.get(reverse("loja:busca"), {"q": "osso"})
        self.assertContains(resposta, "Osso")
        self.assertNotContains(resposta, "Bola")

    def test_busca_ignora_acentos_e_maiusculas(self):
        for termo in ("racao", "RAÇÃO"):
            resposta = self.client.get(reverse("loja:busca"), {"q": termo})
            self.assertEqual(set(self.slugs(resposta)), {"racao", "racao-gato"}, termo)
        self.assertEqual(self.slugs(self.client.get(reverse("loja:busca"), {"q": "ração gato"})), ["racao-gato"])
        sugestoes = self.client.get(reverse("loja:sugestoes"), {"q": "racao"}).json()["itens"]
        self.assertEqual({item["nome"] for item in sugestoes}, {"Ração", "Ração Gato"})

    def test_filtros_por_departamento_marca_e_faixa(self):
        self.assertEqual(self.slugs(self.client.get(self.c["caes"].get_absolute_url(), {"depto": "brinquedos"})), ["bola", "osso"])
        resposta = self.client.get(reverse("loja:busca"), {"marca": "X"})
        self.assertEqual(set(self.slugs(resposta)), {"racao", "racao-gato"})
        self.assertEqual(self.slugs(self.client.get(reverse("loja:busca"), {"faixa": "50-100"})), ["racao"])

    def test_filtro_por_subdepartamento(self):
        resposta = self.client.get(reverse("loja:busca"), {"sub": "racao-umida"})
        self.assertEqual(self.slugs(resposta), ["racao-gato"])

    def test_opcoes_de_subdepartamento_so_aparecem_com_departamento(self):
        url = reverse("loja:busca")
        self.assertEqual(len(self.client.get(url).context["opcoes"].subdepartamentos), 0)
        opcoes = self.client.get(url, {"depto": "racoes"}).context["opcoes"]
        self.assertEqual([s.slug for s in opcoes.subdepartamentos], ["racao-seca", "racao-umida"])
        pagina_do_departamento = self.client.get(self.c["racoes"].get_absolute_url()).context["opcoes"]
        self.assertEqual(len(pagina_do_departamento.subdepartamentos), 2)

    def test_filtro_de_ofertas_e_ordenacao(self):
        self.assertEqual(self.slugs(self.client.get(reverse("loja:busca"), {"promo": "1"})), ["racao"])
        resposta = self.client.get(reverse("loja:busca"), {"ordem": "menor-preco"})
        self.assertEqual(self.slugs(resposta)[0], "osso")

    def test_paginacao(self):
        for i in range(15):
            Produto.objects.create(
                categoria=self.c["caes"], nome=f"Extra {i}", slug=f"extra-{i}", preco=Decimal("5.00"), estoque=1,
            )
        resposta = self.client.get(reverse("loja:busca"))
        self.assertEqual(len(resposta.context["pagina"]), 12)
        self.assertEqual(resposta.context["pagina"].paginator.num_pages, 2)
        self.assertEqual(self.client.get(reverse("loja:busca"), {"pagina": "999"}).status_code, 200)

    def test_sugestoes(self):
        resposta = self.client.get(reverse("loja:sugestoes"), {"q": "raç"})
        self.assertEqual({item["nome"] for item in resposta.json()["itens"]}, {"Ração", "Ração Gato"})
        self.assertEqual(self.client.get(reverse("loja:sugestoes"), {"q": "r"}).json(), {"itens": []})

    def test_produto_inativo_nao_aparece(self):
        self.c["racao"].ativo = False
        self.c["racao"].save()
        self.assertEqual(self.client.get(self.c["racao"].get_absolute_url()).status_code, 404)

    def test_menu_lista_departamentos_do_animal(self):
        html = self.client.get(reverse("loja:home")).content.decode()
        gatos = html[html.index('data-animal="gatos"'):]
        self.assertIn("Rações", gatos[:gatos.index("</li>")])
        self.assertNotIn("Brinquedos", gatos[:gatos.index("</li>")])


class MenuSubdepartamentosTests(TestCase):
    def setUp(self):
        call_command("seed", verbosity=0)

    def bloco_do_animal(self, slug, proximo):
        html = self.client.get(reverse("loja:home")).content.decode()
        return html[html.index(f'data-animal="{slug}"'):html.index(f'data-animal="{proximo}"')]

    def test_departamento_com_varios_tipos_abre_submenu(self):
        gatos = self.bloco_do_animal("gatos", "passaros")
        self.assertIn("mega__sub", gatos)
        self.assertIn("depto=racoes&amp;sub=racao-seca", gatos)
        self.assertIn("Ração Úmida e Sachês", gatos)

    def test_departamento_com_um_tipo_nao_abre_submenu(self):
        gatos = self.bloco_do_animal("gatos", "passaros")
        bloco = gatos[gatos.index("Transporte"):]
        self.assertNotIn("mega__sub", bloco[:bloco.index("</li>")])

    def test_tipos_listados_sao_so_do_animal(self):
        caes = self.bloco_do_animal("caes", "gatos")
        gatos = self.bloco_do_animal("gatos", "passaros")
        self.assertIn("Light e Controle de Peso", caes)
        self.assertNotIn("Light e Controle de Peso", gatos)

    def test_animal_sem_variedade_de_tipos_nao_tem_submenu(self):
        self.assertNotIn("mega__sub", self.bloco_do_animal("peixes", "roedores"))


class SeedTests(TestCase):
    def test_seed_e_idempotente_e_gera_paginas(self):
        call_command("seed", verbosity=0)
        total = Produto.objects.count()
        call_command("seed", verbosity=0)
        self.assertEqual(Produto.objects.count(), total)
        self.assertGreaterEqual(total, 50)
        for produto in Produto.objects.all():
            self.assertEqual(self.client.get(produto.get_absolute_url()).status_code, 200, produto.slug)

    def test_limpar_remove_so_o_que_nao_e_do_catalogo_demo(self):
        criar_catalogo()
        call_command("seed", "--limpar", verbosity=0)
        self.assertFalse(Produto.objects.filter(slug="racao").exists())
        self.assertTrue(Produto.objects.filter(slug="racao-premium-adultos-frango-e-arroz-15kg").exists())
