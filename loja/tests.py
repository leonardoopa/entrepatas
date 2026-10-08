from decimal import Decimal

from django.contrib.auth import get_user_model
import re

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Departamento, Pedido, Produto

User = get_user_model()

DADOS_CADASTRO = {
    "nome": "Maria", "email": "Maria@Example.com", "senha": "Gatinho!2024x", "senha2": "Gatinho!2024x",
}

DADOS_ENTREGA = {
    "nome": "Ana", "email": "ana@example.com", "telefone": "",
    "cep": "01001-000", "endereco": "Rua A, 1", "cidade": "São Paulo", "uf": "sp",
}


class LojaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Categoria.objects.create(nome="Cães", slug="caes", emoji="🐶")
        cls.gatos = Categoria.objects.create(nome="Gatos", slug="gatos", emoji="🐱")
        cls.racoes = Departamento.objects.create(nome="Rações", slug="racoes")
        cls.brinq = Departamento.objects.create(nome="Brinquedos", slug="brinquedos")
        cls.racao = Produto.objects.create(
            categoria=cls.cat, departamento=cls.racoes, nome="Ração", slug="racao", marca="X",
            preco=Decimal("100.00"), preco_promocional=Decimal("80.00"), estoque=5, vendas=10,
        )
        cls.bola = Produto.objects.create(
            categoria=cls.cat, departamento=cls.brinq, nome="Bola", slug="bola", marca="Y",
            preco=Decimal("30.00"), estoque=50, vendas=99,
        )
        cls.gato = Produto.objects.create(
            categoria=cls.gatos, departamento=cls.racoes, nome="Ração Gato", slug="racao-gato", marca="X",
            preco=Decimal("250.00"), estoque=9,
        )
        cls.sem_estoque = Produto.objects.create(
            categoria=cls.cat, departamento=cls.brinq, nome="Osso", slug="osso",
            preco=Decimal("10.00"), estoque=0,
        )

    # --- páginas ---
    def test_paginas_publicas(self):
        for url in [
            reverse("loja:home"),
            reverse("loja:ofertas"),
            self.cat.get_absolute_url(),
            self.racoes.get_absolute_url(),
            self.racao.get_absolute_url(),
            reverse("loja:busca") + "?q=ra",
            reverse("loja:carrinho"),
            reverse("loja:minicarrinho"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_seed_gera_catalogo_e_paginas(self):
        call_command("seed", verbosity=0)
        call_command("seed", verbosity=0)  # idempotente
        total = Produto.objects.count()
        self.assertGreaterEqual(total, 50)
        self.assertEqual(self.client.get(reverse("loja:home")).status_code, 200)
        for p in Produto.objects.exclude(slug__in=["racao", "bola", "racao-gato", "osso"])[:60]:
            self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200, p.slug)

    # --- preço ---
    def test_preco_promocional(self):
        self.assertEqual(self.racao.preco_final, Decimal("80.00"))
        self.assertEqual(self.racao.desconto_percentual, 20)

    def test_parcelas_sem_juros(self):
        self.assertEqual(self.racao.parcelas, (3, Decimal("26.67")))
        self.assertEqual(self.sem_estoque.parcelas, (1, Decimal("10.00")))

    # --- filtros ---
    def test_busca_filtra(self):
        resp = self.client.get(reverse("loja:busca"), {"q": "osso"})
        self.assertContains(resp, "Osso")
        self.assertNotContains(resp, "Bola")

    def test_filtro_por_departamento_marca_e_faixa(self):
        url = self.cat.get_absolute_url()
        self.assertEqual(
            [p.slug for p in self.client.get(url, {"depto": "brinquedos"}).context["pagina"]],
            ["bola", "osso"],
        )
        resp = self.client.get(reverse("loja:busca"), {"marca": "X"})
        self.assertEqual({p.slug for p in resp.context["pagina"]}, {"racao", "racao-gato"})
        resp = self.client.get(reverse("loja:busca"), {"faixa": "50-100"})
        self.assertEqual([p.slug for p in resp.context["pagina"]], ["racao"])  # usa o preço promocional

    def test_filtro_promocao_e_ordenacao(self):
        resp = self.client.get(reverse("loja:busca"), {"promo": "1"})
        self.assertEqual([p.slug for p in resp.context["pagina"]], ["racao"])
        resp = self.client.get(reverse("loja:busca"), {"ordem": "menor-preco"})
        self.assertEqual(resp.context["pagina"][0].slug, "osso")
        resp = self.client.get(reverse("loja:busca"), {"ordem": "invalida"})
        self.assertEqual(resp.context["ordem"], "relevancia")

    def test_paginacao(self):
        for i in range(15):
            Produto.objects.create(
                categoria=self.cat, nome=f"Extra {i}", slug=f"extra-{i}", preco=Decimal("5.00"), estoque=1,
            )
        resp = self.client.get(reverse("loja:busca"))
        self.assertEqual(len(resp.context["pagina"]), 12)
        self.assertEqual(resp.context["pagina"].paginator.num_pages, 2)
        self.assertEqual(self.client.get(reverse("loja:busca"), {"pagina": "999"}).status_code, 200)

    def test_sugestoes(self):
        resp = self.client.get(reverse("loja:sugestoes"), {"q": "raç"})
        self.assertEqual({i["nome"] for i in resp.json()["itens"]}, {"Ração", "Ração Gato"})
        self.assertEqual(self.client.get(reverse("loja:sugestoes"), {"q": "r"}).json(), {"itens": []})

    def test_produto_inativo_nao_aparece(self):
        self.racao.ativo = False
        self.racao.save()
        self.assertEqual(self.client.get(self.racao.get_absolute_url()).status_code, 404)

    # --- carrinho ---
    def test_nao_adiciona_sem_estoque(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.sem_estoque.pk]))
        self.assertFalse(self.client.session.get("carrinho"))

    def test_quantidade_limitada_ao_estoque(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.racao.pk]), {"quantidade": 99})
        self.assertEqual(self.client.session["carrinho"], {str(self.racao.pk): 5})

    def test_quantidade_invalida_vira_um(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.racao.pk]), {"quantidade": "abc"})
        self.assertEqual(self.client.session["carrinho"], {str(self.racao.pk): 1})

    def test_adicionar_via_ajax_devolve_json(self):
        resp = self.client.post(
            reverse("loja:carrinho_adicionar", args=[self.bola.pk]), {"quantidade": 2},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        dados = resp.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["qtd"], 2)
        self.assertIn("Bola", dados["html"])

    def test_ajax_sem_estoque_devolve_erro(self):
        resp = self.client.post(
            reverse("loja:carrinho_adicionar", args=[self.sem_estoque.pk]),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])

    def test_remover_item(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.bola.pk]))
        self.client.post(reverse("loja:carrinho_remover", args=[self.bola.pk]))
        self.assertFalse(self.client.session.get("carrinho"))

    # --- frete ---
    def test_frete_cobrado_abaixo_do_minimo(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.bola.pk]))
        ctx = self.client.get(reverse("loja:carrinho")).context
        self.assertEqual(ctx["frete"], Decimal("19.90"))
        self.assertEqual(ctx["total"], Decimal("49.90"))
        self.assertFalse(ctx["frete_gratis"])
        self.assertEqual(ctx["falta_frete"], Decimal("169.00"))

    def test_frete_gratis_acima_do_minimo(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.gato.pk]))
        ctx = self.client.get(reverse("loja:carrinho")).context
        self.assertEqual(ctx["frete"], Decimal("0"))
        self.assertTrue(ctx["frete_gratis"])
        self.assertEqual(ctx["progresso_frete"], 100)

    # --- checkout ---
    def test_compra_completa_baixa_estoque_e_soma_frete(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.racao.pk]), {"quantidade": 2})
        resp = self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        pedido = Pedido.objects.get()
        self.assertRedirects(resp, reverse("loja:pedido", args=[pedido.pk]))
        self.assertEqual(pedido.uf, "SP")
        self.assertEqual(pedido.subtotal, Decimal("160.00"))
        self.assertEqual(pedido.frete, Decimal("19.90"))
        self.assertEqual(pedido.total, Decimal("179.90"))
        self.racao.refresh_from_db()
        self.assertEqual(self.racao.estoque, 3)
        self.assertEqual(self.racao.vendas, 12)
        self.assertFalse(self.client.session.get("carrinho"))

    def test_checkout_com_frete_gratis(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.gato.pk]))
        self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertEqual(Pedido.objects.get().frete, Decimal("0"))

    def test_checkout_nao_vende_alem_do_estoque(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.racao.pk]), {"quantidade": 5})
        Produto.objects.filter(pk=self.racao.pk).update(estoque=1)  # outro comprador levou o resto
        resp = self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        self.assertRedirects(resp, reverse("loja:carrinho"))
        self.assertEqual(Pedido.objects.count(), 0)

    def test_pedido_so_para_o_comprador(self):
        pedido = Pedido.objects.create(
            nome="Ana", email="a@e.com", cep="1", endereco="x", cidade="y", uf="SP"
        )
        resp = self.client.get(reverse("loja:pedido", args=[pedido.pk]))
        self.assertRedirects(resp, reverse("loja:home"))

    def test_checkout_com_carrinho_vazio_redireciona(self):
        resp = self.client.get(reverse("loja:checkout"))
        self.assertRedirects(resp, reverse("loja:carrinho"))


class ContasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Categoria.objects.create(nome="Cães", slug="caes", emoji="🐶")
        cls.produto = Produto.objects.create(
            categoria=cat, nome="Bola", slug="bola", preco=Decimal("30.00"), estoque=50,
        )
        cls.usuario = User.objects.create_user(
            username="ana@example.com", email="ana@example.com", password="Senha!Forte123", first_name="Ana",
        )

    def test_cadastro_cria_usuario_e_faz_login(self):
        resp = self.client.post(reverse("loja:cadastro"), DADOS_CADASTRO)
        self.assertRedirects(resp, reverse("loja:conta"))
        usuario = User.objects.get(username="maria@example.com")  # e-mail em minúsculas
        self.assertEqual(usuario.first_name, "Maria")
        self.assertTrue(usuario.check_password("Gatinho!2024x"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_cadastro_mantem_o_carrinho(self):
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.produto.pk]))
        self.client.post(reverse("loja:cadastro"), DADOS_CADASTRO)
        self.assertEqual(self.client.session["carrinho"], {str(self.produto.pk): 1})

    def test_cadastro_rejeita_email_repetido_senha_fraca_e_diferente(self):
        url = reverse("loja:cadastro")
        resp = self.client.post(url, {**DADOS_CADASTRO, "email": "ANA@example.com"})
        self.assertContains(resp, "Já existe uma conta com este e-mail.")
        resp = self.client.post(url, {**DADOS_CADASTRO, "senha": "12345678", "senha2": "12345678"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="maria@example.com").exists())
        resp = self.client.post(url, {**DADOS_CADASTRO, "senha2": "outra"})
        self.assertContains(resp, "As senhas não são iguais.")

    def test_cadastro_ignora_next_externo(self):
        resp = self.client.post(reverse("loja:cadastro"), {**DADOS_CADASTRO, "next": "https://evil.example/x"})
        self.assertRedirects(resp, reverse("loja:conta"))
        self.client.logout()
        resp = self.client.post(reverse("loja:cadastro"), {**DADOS_CADASTRO, "email": "b@example.com", "next": "/carrinho/"})
        self.assertRedirects(resp, reverse("loja:carrinho"))

    def test_login_com_email_e_senha(self):
        url = reverse("loja:entrar")
        resp = self.client.post(url, {"username": "ANA@example.com", "password": "Senha!Forte123"})
        self.assertRedirects(resp, reverse("loja:conta"))
        self.client.logout()
        resp = self.client.post(url, {"username": "ana@example.com", "password": "errada"})
        self.assertContains(resp, "E-mail ou senha incorretos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_so_por_post(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("loja:sair")).status_code, 405)
        self.client.post(reverse("loja:sair"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_conta_exige_login(self):
        resp = self.client.get(reverse("loja:conta"))
        self.assertRedirects(resp, f"{reverse('loja:entrar')}?next={reverse('loja:conta')}")

    def test_pedido_fica_na_conta_do_comprador(self):
        self.client.force_login(self.usuario)
        self.client.post(reverse("loja:carrinho_adicionar", args=[self.produto.pk]))
        form = self.client.get(reverse("loja:checkout"))
        self.assertEqual(form.context["form"].initial["email"], "ana@example.com")
        self.client.post(reverse("loja:checkout"), DADOS_ENTREGA)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.usuario, self.usuario)
        self.assertContains(self.client.get(reverse("loja:conta")), f"Pedido #{pedido.pk}")

        # outra pessoa, em outra sessão, não vê o pedido
        outro = self.client_class()
        outro.force_login(User.objects.create_user("c@example.com", "c@example.com", "Senha!Forte123"))
        self.assertRedirects(outro.get(reverse("loja:pedido", args=[pedido.pk])), reverse("loja:home"))
        self.assertNotContains(outro.get(reverse("loja:conta")), f"Pedido #{pedido.pk}")
        # o dono vê o pedido mesmo sem a sessão da compra
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("loja:pedido", args=[pedido.pk])).status_code, 200)

    def test_cabecalho_muda_com_login(self):
        self.assertContains(self.client.get(reverse("loja:home")), "Cadastre-se")
        self.client.force_login(self.usuario)
        resp = self.client.get(reverse("loja:home"))
        self.assertContains(resp, "Olá,")
        self.assertContains(resp, reverse("loja:sair"))

    def test_menu_lista_departamentos_por_animal(self):
        call_command("seed", verbosity=0)
        resp = self.client.get(reverse("loja:home"))
        html = resp.content.decode()
        gatos = html[html.index('data-animal="gatos"'):html.index('data-animal="passaros"')]
        self.assertIn("Rações", gatos)
        self.assertIn("Comedouros e Bebedouros", gatos)
        self.assertNotIn("Camas e Casinhas</a>", html[html.index('data-animal="peixes"'):html.index('data-animal="roedores"')])


class RecuperarSenhaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(
            username="ana@example.com", email="ana@example.com", password="Senha!Forte123", first_name="Ana",
        )

    def _link_do_email(self):
        self.assertEqual(len(mail.outbox), 1)
        achado = re.search(r"https?://testserver(/conta/senha/redefinir/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(achado, mail.outbox[0].body)
        return achado.group(1)

    def test_fluxo_completo(self):
        resp = self.client.post(reverse("loja:senha_recuperar"), {"email": "ana@example.com"})
        self.assertRedirects(resp, reverse("loja:senha_enviada"))
        self.assertEqual(mail.outbox[0].to, ["ana@example.com"])
        self.assertIn("Olá, Ana!", mail.outbox[0].body)

        link = self._link_do_email()
        resp = self.client.get(link, follow=True)  # troca o token da URL por um da sessão
        self.assertTrue(resp.context["validlink"])
        resp = self.client.post(resp.request["PATH_INFO"], {
            "new_password1": "NovaSenha!987xy", "new_password2": "NovaSenha!987xy",
        })
        self.assertRedirects(resp, reverse("loja:senha_concluida"))

        self.assertFalse(self.client.login(username="ana@example.com", password="Senha!Forte123"))
        self.assertTrue(self.client.login(username="ana@example.com", password="NovaSenha!987xy"))

    def test_link_so_funciona_uma_vez(self):
        self.client.post(reverse("loja:senha_recuperar"), {"email": "ana@example.com"})
        link = self._link_do_email()
        resp = self.client.get(link, follow=True)
        self.client.post(resp.request["PATH_INFO"], {
            "new_password1": "NovaSenha!987xy", "new_password2": "NovaSenha!987xy",
        })
        resp = self.client.get(link, follow=True)
        self.assertFalse(resp.context["validlink"])
        self.assertContains(resp, "Link inválido")

    def test_link_invalido(self):
        resp = self.client.get(reverse("loja:senha_redefinir", args=["abc", "token-falso"]), follow=True)
        self.assertContains(resp, "Link inválido")

    def test_email_desconhecido_nao_revela_nada(self):
        resp = self.client.post(reverse("loja:senha_recuperar"), {"email": "ninguem@example.com"})
        self.assertRedirects(resp, reverse("loja:senha_enviada"))
        self.assertEqual(len(mail.outbox), 0)

    def test_senha_fraca_e_rejeitada(self):
        self.client.post(reverse("loja:senha_recuperar"), {"email": "ana@example.com"})
        resp = self.client.get(self._link_do_email(), follow=True)
        resp = self.client.post(resp.request["PATH_INFO"], {"new_password1": "12345678", "new_password2": "12345678"})
        self.assertEqual(resp.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Senha!Forte123"))

    def test_login_tem_link_para_recuperar(self):
        self.assertContains(self.client.get(reverse("loja:entrar")), reverse("loja:senha_recuperar"))


class LogoTests(TestCase):
    def test_cabecalho_usa_logo_e_favicon(self):
        html = self.client.get(reverse("loja:home")).content.decode()
        self.assertIn("loja/logo.png", html)
        self.assertIn("loja/favicon.png", html)
