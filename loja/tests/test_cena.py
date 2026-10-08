from django.test import TestCase
from django.urls import reverse

from loja.cena import FIGURAS_POR_LADO, VARIANTES, Lado, montar_cena, montar_figuras

from .fabricas import criar_catalogo


class FigurasTests(TestCase):
    def test_quantidade_e_determinismo(self):
        figuras = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes")
        self.assertEqual(len(figuras), FIGURAS_POR_LADO)
        self.assertEqual(figuras, montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes"))

    def test_cada_lado_fica_na_sua_metade(self):
        esquerda = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes")
        direita = montar_figuras(FIGURAS_POR_LADO, Lado.DIREITO, "gatos")
        self.assertTrue(all(f.x < 36 for f in esquerda))
        self.assertTrue(all(f.x > 64 for f in direita))

    def test_entrada_escalonada_dentro_da_linha_do_tempo(self):
        inicios = sorted(f.inicio for f in montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes"))
        self.assertTrue(all(0 <= i < 0.8 for i in inicios))
        self.assertEqual(len(set(inicios)), FIGURAS_POR_LADO)

    def test_usa_todas_as_variantes_de_cada_lado(self):
        for lado, semente in ((Lado.ESQUERDO, "caes"), (Lado.DIREITO, "gatos")):
            variantes = {f.variante for f in montar_figuras(FIGURAS_POR_LADO, lado, semente)}
            self.assertEqual(variantes, set(range(VARIANTES)))

    def test_estilo_nao_usa_virgula_decimal(self):
        for figura in montar_figuras(FIGURAS_POR_LADO, Lado.DIREITO, "gatos"):
            self.assertNotIn(",", figura.estilo)


class CenaNaHomeTests(TestCase):
    def test_home_mostra_a_cena_com_as_figuras_dos_dois_lados(self):
        criar_catalogo()
        html = self.client.get(reverse("loja:home")).content.decode()
        self.assertIn("data-cena", html)
        self.assertEqual(html.count('class="figura"'), 2 * FIGURAS_POR_LADO)
        self.assertIn("Comprar agora", html)
        self.assertNotIn("data-cena-tempo", html)

    def test_cada_variante_gera_um_desenho_diferente(self):
        criar_catalogo()
        html = self.client.get(reverse("loja:home")).content.decode()
        inicio = html.index("data-cena")
        desenhos = {
            trecho.split("</span></span>")[0]
            for trecho in html[inicio:].split('<span class="figura__corpo">')[1:]
        }
        self.assertGreaterEqual(len(desenhos), 2 * VARIANTES)

    def test_sem_caes_e_gatos_a_cena_nao_aparece(self):
        resposta = self.client.get(reverse("loja:home"))
        self.assertNotContains(resposta, "data-cena")

    def test_montar_cena_usa_as_categorias_recebidas(self):
        c = criar_catalogo()
        cena = montar_cena(c["caes"], c["gatos"], quantidade=6)
        self.assertEqual((len(cena.figuras_caes), len(cena.figuras_gatos)), (6, 6))
