import re
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from loja.backoffice.erros import BackofficeIndisponivel, BackofficeNaoEncontrado, BackofficeRecusou

DADOS_ENTREGA = {
    "nome": "Ana", "email": "ana@example.com", "telefone": "",
    "cep": "01001-000", "endereco": "Rua A, 1", "cidade": "São Paulo", "uf": "sp",
}
SENHA = "Senha!Forte123"

CAES = ("caes", "Cães", "🐶")
GATOS = ("gatos", "Gatos", "🐱")
RACOES = ("racoes", "Rações")
BRINQUEDOS = ("brinquedos", "Brinquedos")
SECA = ("racao-seca", "Ração Seca", "racoes")
UMIDA = ("racao-umida", "Ração Úmida", "racoes")


def produto_json(sku, nome, animal, preco="100.00", promo=None, estoque=10, departamento=None, sub=None,
                 marca=None, grupo=None, variacao="", imagens=(), avaliacao="4.5", promocao_fim=None):
    return {
        "sku": sku, "slug": sku.lower(), "nome": nome, "descricao": f"Descrição de {nome}.", "gtin": "",
        "marca": {"slug": marca.lower(), "nome": marca} if marca else None,
        "animal": {"slug": animal[0], "nome": animal[1], "emoji": animal[2]},
        "departamento": {"slug": departamento[0], "nome": departamento[1]} if departamento else None,
        "subdepartamento": {"slug": sub[0], "nome": sub[1], "departamento": sub[2]} if sub else None,
        "grupo": {"slug": grupo.lower(), "nome": grupo} if grupo else None, "variacao": variacao,
        "preco": preco, "preco_promocional": promo, "promocao_fim": promocao_fim,
        "preco_final": promo or preco, "estoque": estoque, "avaliacao": avaliacao, "num_avaliacoes": 12,
        "arte": {"tipo": "saco", "cor": "#D96C4A", "imagem_url": imagens[0] if imagens else ""}, "imagens": list(imagens),
    }


def catalogo_padrao():
    return [
        produto_json("RAC-1", "Ração", CAES, "100.00", "80.00", 5, RACOES, SECA, "NutriPet"),
        produto_json("BOL-1", "Bola", CAES, "30.00", None, 50, BRINQUEDOS, None, "PataFeliz"),
        produto_json("RAC-G", "Ração Gato", GATOS, "250.00", None, 9, RACOES, UMIDA, "NutriPet"),
        produto_json("OSS-1", "Osso", CAES, "10.00", None, 0, BRINQUEDOS, None, "PataFeliz"),
    ]


class BackofficeFalso:
    """Imita a API do backoffice em memória (mesmo formato de resposta) para os testes não dependerem da rede."""

    def __init__(self, produtos=None):
        self.produtos = list(produtos if produtos is not None else catalogo_padrao())
        self.pedidos: dict[str, dict] = {}
        self.vitrines_json: dict | None = None
        self.indisponivel = False
        self.falhar_pedido: tuple[int, dict] | None = None
        self.chamadas: list[tuple[str, str, object]] = []

    # --- cliente HTTP ---
    def get(self, caminho, params=None):
        self._registrar("GET", caminho, params)
        if self.indisponivel:
            raise BackofficeIndisponivel("fora do ar")
        consulta = self._consulta(params)
        if caminho == "catalogo/taxonomia/":
            return self._taxonomia()
        if caminho == "catalogo/produtos/":
            return self._listar(consulta)
        if achado := re.fullmatch(r"catalogo/produtos/([^/]+)/", caminho):
            return self._detalhe(achado.group(1))
        if caminho == "vitrines/":
            return self.vitrines_json if self.vitrines_json is not None else self._vitrines_padrao()
        if achado := re.fullmatch(r"pedidos/([^/]+)/", caminho):
            if achado.group(1) not in self.pedidos:
                raise BackofficeNaoEncontrado(caminho)
            return self.pedidos[achado.group(1)]
        if achado := re.fullmatch(r"clientes/([^/]+)/pedidos/", caminho):
            return {"itens": [p for p in self.pedidos.values() if (p["cliente"] or {}).get("id_externo") == achado.group(1)]}
        raise BackofficeNaoEncontrado(caminho)

    def post(self, caminho, json):
        self._registrar("POST", caminho, json)
        if self.indisponivel:
            raise BackofficeIndisponivel("fora do ar")
        if self.falhar_pedido:
            raise BackofficeRecusou(*self.falhar_pedido)
        numero = json["numero_externo"]
        if numero in self.pedidos:
            return 200, {"id": 1, "numero_externo": numero, "total": self.pedidos[numero]["total"]}
        linhas = []
        for item in json["itens"]:
            produto = next((p for p in self.produtos if p["sku"] == item["sku"]), None)
            if produto is None:
                raise BackofficeRecusou(422, {"erro": "Produto indisponível no site", "sku": item["sku"]})
            if produto["estoque"] < item["quantidade"]:
                raise BackofficeRecusou(409, {"erro": "Estoque insuficiente.", "sku": item["sku"], "disponivel": produto["estoque"]})
            linhas.append((produto, item["quantidade"]))
        for produto, quantidade in linhas:
            produto["estoque"] -= quantidade
        subtotal = sum(Decimal(p["preco_final"]) * q for p, q in linhas)
        frete = Decimal(json["frete"])
        self.pedidos[numero] = {
            "numero_externo": numero, "status": "novo", "pagamento": {"forma": "", "status": "pendente", "parcelas": 1},
            "subtotal": f"{subtotal:.2f}", "frete": f"{frete:.2f}", "total": f"{subtotal + frete:.2f}",
            "comprado_em": datetime.now(timezone.utc).isoformat(), "cliente": json["cliente"], "entrega": json["entrega"],
            "itens": [
                {"sku": p["sku"], "descricao": p["nome"], "quantidade": q, "preco_unitario": p["preco_final"]} for p, q in linhas
            ],
            "historico_status": [],
        }
        return 201, {"id": len(self.pedidos), "numero_externo": numero, "total": self.pedidos[numero]["total"]}

    # --- internos ---
    def _registrar(self, metodo, caminho, dados):
        self.chamadas.append((metodo, caminho, dados))

    @staticmethod
    def _consulta(params):
        consulta: dict[str, list[str]] = {}
        for nome, valor in (params.items() if isinstance(params, dict) else params or ()):
            consulta.setdefault(nome, []).append(str(valor))
        return consulta

    def _escopo(self, consulta):
        itens = self.produtos
        if "sku" in consulta:
            itens = [p for p in itens if p["sku"] in consulta["sku"]]
        if "escopo_animal" in consulta:
            itens = [p for p in itens if p["animal"]["slug"] == consulta["escopo_animal"][0]]
        if "escopo_departamento" in consulta:
            itens = [p for p in itens if (p["departamento"] or {}).get("slug") == consulta["escopo_departamento"][0]]
        if consulta.get("escopo_ofertas") == ["1"]:
            itens = [p for p in itens if p["preco_promocional"]]
        if "q" in consulta:
            termo = consulta["q"][0].lower()
            itens = [p for p in itens if termo in p["nome"].lower() or termo in ((p["marca"] or {}).get("nome", "")).lower()]
        return itens

    def _filtrar(self, itens, consulta):
        for parametro, extrair in (
            ("animal", lambda p: p["animal"]["slug"]),
            ("departamento", lambda p: (p["departamento"] or {}).get("slug")),
            ("subdepartamento", lambda p: (p["subdepartamento"] or {}).get("slug")),
            ("marca", lambda p: (p["marca"] or {}).get("slug")),
        ):
            if parametro in consulta:
                itens = [p for p in itens if extrair(p) in consulta[parametro]]
        if consulta.get("promo") == ["1"]:
            itens = [p for p in itens if p["preco_promocional"]]
        faixas = {"ate-50": (None, 50), "50-100": (50, 100), "100-200": (100, 200), "acima-200": (200, None)}
        if consulta.get("faixa", [""])[0] in faixas:
            minimo, maximo = faixas[consulta["faixa"][0]]
            itens = [p for p in itens if (minimo is None or Decimal(p["preco_final"]) >= minimo) and (maximo is None or Decimal(p["preco_final"]) < maximo)]
        ordem = consulta.get("ordem", ["relevancia"])[0]
        chave = {"menor-preco": lambda p: Decimal(p["preco_final"]), "maior-preco": lambda p: -Decimal(p["preco_final"])}.get(ordem, lambda p: p["nome"])
        return sorted(itens, key=chave)

    def _listar(self, consulta):
        base = self._escopo(consulta)
        itens = self._filtrar(base, consulta)
        tamanho = int(consulta.get("tamanho", ["24"])[0])
        total_paginas = max(1, -(-len(itens) // tamanho))
        pagina = min(max(int(consulta.get("pagina", ["1"])[0]), 1), total_paginas)
        departamentos = {p["departamento"]["slug"]: p["departamento"] for p in base if p["departamento"]}
        escopo_deps = consulta.get("departamento") or (list(departamentos) if len(departamentos) == 1 else [])
        subs = {p["subdepartamento"]["slug"]: p["subdepartamento"] for p in base if p["subdepartamento"] and p["subdepartamento"]["departamento"] in escopo_deps}
        marcas = {p["marca"]["slug"]: p["marca"] for p in base if p["marca"]}
        return {
            "total": len(itens), "pagina": pagina, "paginas": total_paginas, "tamanho": tamanho,
            "itens": itens[(pagina - 1) * tamanho:pagina * tamanho],
            "facetas": {
                "animais": list({p["animal"]["slug"]: p["animal"] for p in base}.values()),
                "departamentos": list(departamentos.values()), "subdepartamentos": list(subs.values()),
                "marcas": sorted(marcas.values(), key=lambda m: m["nome"]),
            },
        }

    def _detalhe(self, slug):
        produto = next((p for p in self.produtos if p["slug"] == slug), None)
        if produto is None:
            raise BackofficeNaoEncontrado(slug)
        irmaos = [p for p in self.produtos if produto["grupo"] and p["grupo"] == produto["grupo"]]
        return {**produto, "variacoes": [
            {"sku": p["sku"], "slug": p["slug"], "variacao": p["variacao"], "preco_final": p["preco_final"], "estoque": p["estoque"]}
            for p in sorted(irmaos, key=lambda p: Decimal(p["preco_final"]))
        ]}

    def _taxonomia(self):
        animais: dict[str, dict] = {}
        for p in self.produtos:
            animal = animais.setdefault(p["animal"]["slug"], {**p["animal"], "departamentos": {}})
            if p["departamento"]:
                dep = animal["departamentos"].setdefault(p["departamento"]["slug"], {**p["departamento"], "subdepartamentos": {}})
                if p["subdepartamento"]:
                    dep["subdepartamentos"][p["subdepartamento"]["slug"]] = p["subdepartamento"]
        return {"animais": [
            {**a, "departamentos": [{**d, "subdepartamentos": list(d["subdepartamentos"].values())} for d in a["departamentos"].values()]}
            for a in animais.values()
        ]}

    def _vitrines_padrao(self):
        return {
            "ofertas": {"nome": "Ofertas imperdíveis", "itens": [p for p in self.produtos if p["preco_promocional"]]},
            "mais_vendidos": {"nome": "Mais vendidos", "itens": self.produtos[:3]},
            "destaques": {"nome": "Destaques", "itens": []},
        }


@override_settings(BACKOFFICE_CACHE_SEGUNDOS=0)
class BackofficeTestCase(TestCase):
    """Base dos testes do site: troca o cliente HTTP do backoffice por um falso e limpa o cache."""

    produtos_iniciais = None

    def setUp(self):
        super().setUp()
        cache.clear()
        self.bo = BackofficeFalso(self.produtos_iniciais() if callable(self.produtos_iniciais) else self.produtos_iniciais)
        patcher = patch("loja.backoffice._cliente", return_value=self.bo)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cache.clear)


def criar_usuario(email="ana@example.com", nome="Ana", senha=SENHA):
    return get_user_model().objects.create_user(username=email, email=email, password=senha, first_name=nome)
