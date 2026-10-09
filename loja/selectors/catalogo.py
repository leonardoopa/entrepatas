from dataclasses import dataclass

from django.http import QueryDict

from loja.dominio import AnimalRef, DepartamentoRef, ItemMenu

ORDEM_PADRAO = "relevancia"
OPCOES_ORDENACAO = [
    ("relevancia", "Mais vendidos"),
    ("menor-preco", "Menor preço"),
    ("maior-preco", "Maior preço"),
    ("nome", "Nome (A-Z)"),
    ("novidades", "Novidades"),
]
OPCOES_FAIXA = [
    ("ate-50", "Até R$ 50"),
    ("50-100", "R$ 50 a R$ 100"),
    ("100-200", "R$ 100 a R$ 200"),
    ("acima-200", "Acima de R$ 200"),
]
ORDENACOES_VALIDAS = {chave for chave, _ in OPCOES_ORDENACAO}
FAIXAS_VALIDAS = {chave for chave, _ in OPCOES_FAIXA}


@dataclass(frozen=True)
class Escopo:
    """O que define a página (animal, departamento, ofertas ou busca). As facetas são calculadas sobre ele."""

    animal: str = ""
    departamento: str = ""
    ofertas: bool = False
    termo: str = ""


@dataclass(frozen=True)
class FiltrosListagem:
    departamentos: tuple[str, ...] = ()
    subdepartamentos: tuple[str, ...] = ()
    animais: tuple[str, ...] = ()
    marcas: tuple[str, ...] = ()
    faixa: str = ""
    somente_ofertas: bool = False
    ordem: str = ORDEM_PADRAO

    @classmethod
    def de_querydict(cls, params: QueryDict) -> "FiltrosListagem":
        faixa, ordem = params.get("faixa", ""), params.get("ordem", ORDEM_PADRAO)
        return cls(
            departamentos=tuple(params.getlist("depto")),
            subdepartamentos=tuple(params.getlist("sub")),
            animais=tuple(params.getlist("animal")),
            marcas=tuple(params.getlist("marca")),
            faixa=faixa if faixa in FAIXAS_VALIDAS else "",
            somente_ofertas=params.get("promo") == "1",
            ordem=ordem if ordem in ORDENACOES_VALIDAS else ORDEM_PADRAO,
        )

    @property
    def ativos(self) -> bool:
        return bool(
            self.departamentos or self.subdepartamentos or self.animais or self.marcas
            or self.faixa or self.somente_ofertas
        )


def parametros_da_api(escopo: Escopo, filtros: FiltrosListagem) -> list[tuple[str, str]]:
    parametros = [
        ("escopo_animal", escopo.animal), ("escopo_departamento", escopo.departamento),
        ("escopo_ofertas", "1" if escopo.ofertas else ""), ("q", escopo.termo),
        ("faixa", filtros.faixa), ("promo", "1" if filtros.somente_ofertas else ""), ("ordem", filtros.ordem),
    ]
    parametros += [("animal", v) for v in filtros.animais]
    parametros += [("departamento", v) for v in filtros.departamentos]
    parametros += [("subdepartamento", v) for v in filtros.subdepartamentos]
    parametros += [("marca", v) for v in filtros.marcas]
    return [(nome, valor) for nome, valor in parametros if valor]


def achar_animal(menu: list[ItemMenu], slug: str) -> AnimalRef | None:
    return next((item.categoria for item in menu if item.categoria.slug == slug), None)


def achar_departamento(menu: list[ItemMenu], slug: str) -> DepartamentoRef | None:
    return next((e.departamento for item in menu for e in item.departamentos if e.departamento.slug == slug), None)


def departamentos_do_menu(menu: list[ItemMenu]) -> list[DepartamentoRef]:
    vistos: dict[str, DepartamentoRef] = {}
    for item in menu:
        for entrada in item.departamentos:
            vistos.setdefault(entrada.departamento.slug, entrada.departamento)
    return list(vistos.values())


def par_caes_e_gatos(menu: list[ItemMenu]) -> tuple[AnimalRef, AnimalRef] | None:
    caes, gatos = achar_animal(menu, "caes"), achar_animal(menu, "gatos")
    return (caes, gatos) if caes and gatos else None
