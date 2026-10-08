import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from loja.cena import FIGURAS_POR_LADO, LIMITE_POUCAS_FOTOS, MINIMO_FOTOS, VARIANTES, Lado, listar_fotos, montar_cena, montar_figuras

from .fabricas import criar_catalogo


class SemFotosNoDisco:
    def setUp(self):
        super().setUp()
        patcher = patch("loja.cena.listar_fotos", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)


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


class CenaNaHomeTests(SemFotosNoDisco, TestCase):
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


class FotosReaisTests(SemFotosNoDisco, TestCase):
    def fotos(self, quantidade, animal="caes"):
        return [f"loja/cena/{animal}/{animal}-{i:02d}.webp" for i in range(quantidade)]

    def test_listar_fotos_filtra_extensoes_e_ordena(self):
        with tempfile.TemporaryDirectory() as base:
            pasta = Path(base) / "caes"
            pasta.mkdir()
            for nome in ("b.webp", "a.JPG", "c.png", "leia-me.txt"):
                (pasta / nome).write_bytes(b"x")
            self.assertEqual(
                listar_fotos("caes", Path(base)),
                ["loja/cena/caes/a.JPG", "loja/cena/caes/b.webp", "loja/cena/caes/c.png"],
            )
            self.assertEqual(listar_fotos("gatos", Path(base)), [])

    def test_cada_foto_aparece_uma_vez_e_define_a_quantidade_de_figuras(self):
        fotos = self.fotos(MINIMO_FOTOS + 1)
        figuras = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes", fotos)
        self.assertEqual(sorted(f.foto for f in figuras), sorted(fotos))

    def test_com_muitas_fotos_limita_ao_maximo_por_lado(self):
        figuras = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes", self.fotos(FIGURAS_POR_LADO + 5))
        self.assertEqual(len(figuras), FIGURAS_POR_LADO)
        self.assertEqual(len({f.foto for f in figuras}), FIGURAS_POR_LADO)

    def test_poucas_fotos_ficam_maiores_e_em_duas_colunas(self):
        poucas = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes", self.fotos(LIMITE_POUCAS_FOTOS))
        muitas = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes", self.fotos(FIGURAS_POR_LADO))
        self.assertGreater(min(f.tamanho for f in poucas), max(f.tamanho for f in muitas) - 0.5)
        self.assertLessEqual(len({round(f.x / 10) for f in poucas}), 2)

    def test_com_poucas_fotos_mantem_os_desenhos(self):
        figuras = montar_figuras(FIGURAS_POR_LADO, Lado.ESQUERDO, "caes", self.fotos(MINIMO_FOTOS - 1))
        self.assertEqual(len(figuras), FIGURAS_POR_LADO)
        self.assertTrue(all(f.foto == "" for f in figuras))

    def test_home_usa_as_fotos_quando_existem(self):
        criar_catalogo()
        with patch("loja.cena.listar_fotos", side_effect=lambda animal: self.fotos(FIGURAS_POR_LADO, animal)):
            html = self.client.get(reverse("loja:home")).content.decode()
        self.assertEqual(html.count('class="figura__foto"'), 2 * FIGURAS_POR_LADO)
        self.assertIn("loja/cena/gatos/gatos-00.webp", html)

    def test_home_sem_fotos_usa_os_desenhos(self):
        criar_catalogo()
        html = self.client.get(reverse("loja:home")).content.decode()
        self.assertNotIn("figura__foto", html)


class PrepararFotosCenaTests(TestCase):
    def test_recorta_reduz_e_converte(self):
        with tempfile.TemporaryDirectory() as raiz:
            origem, destino = Path(raiz) / "origem", Path(raiz) / "destino"
            origem.mkdir()
            Image.new("RGB", (1000, 600), (200, 120, 60)).save(origem / "meu cachorro.jpg")
            Image.new("RGB", (300, 900), (60, 120, 200)).save(origem / "outro.png")
            (origem / "notas.txt").write_text("ignorar")

            call_command("preparar_fotos_cena", str(origem), "caes", "--tamanho", "120", "--destino", str(destino), verbosity=0)

            arquivos = sorted((destino / "caes").iterdir())
            self.assertEqual([a.name for a in arquivos], ["caes-01.webp", "caes-02.webp"])
            with Image.open(arquivos[0]) as imagem:
                self.assertEqual((imagem.size, imagem.format), ((120, 120), "WEBP"))

    def test_nao_amplia_foto_pequena_e_foca_na_parte_de_cima(self):
        with tempfile.TemporaryDirectory() as raiz:
            origem, destino = Path(raiz) / "origem", Path(raiz) / "destino"
            origem.mkdir()
            foto = Image.new("RGB", (100, 300), (255, 255, 255))
            foto.paste((255, 0, 0), (0, 0, 100, 100))
            foto.save(origem / "alta.png")

            call_command("preparar_fotos_cena", str(origem), "gatos", "--destino", str(destino), verbosity=0)

            with Image.open(destino / "gatos" / "gatos-01.webp") as imagem:
                self.assertEqual(imagem.size, (100, 100))
                rgb = imagem.convert("RGB")
                self.assertLess(rgb.getpixel((50, 5))[1], 120)
                self.assertGreater(rgb.getpixel((50, 95))[1], 200)

    def test_pasta_sem_fotos_gera_erro(self):
        with tempfile.TemporaryDirectory() as raiz:
            with self.assertRaises(CommandError):
                call_command("preparar_fotos_cena", raiz, "gatos", verbosity=0)

    def test_pasta_inexistente_gera_erro(self):
        with self.assertRaises(CommandError):
            call_command("preparar_fotos_cena", "/nao/existe", "gatos", verbosity=0)
