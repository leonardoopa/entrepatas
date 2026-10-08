from dataclasses import dataclass

from django.db.models import Q, QuerySet
from django.db.models.functions import Coalesce
from django.http import QueryDict

from loja.models import Categoria, Departamento, Produto, Subdepartamento
from loja.texto import normalizar

ORDEM_PADRAO = "relevancia"
ORDENACOES = {
    "relevancia": ("Mais vendidos", "-vendas"),
    "menor-preco": ("Menor preço", "valor"),
    "maior-preco": ("Maior preço", "-valor"),
    "nome": ("Nome (A-Z)", "nome"),
    "novidades": ("Novidades", "-criado_em"),
}
FAIXAS = {
    "ate-50": ("Até R$ 50", None, 50),
    "50-100": ("R$ 50 a R$ 100", 50, 100),
    "100-200": ("R$ 100 a R$ 200", 100, 200),
    "acima-200": ("Acima de R$ 200", 200, None),
}
OPCOES_ORDENACAO = [(chave, rotulo) for chave, (rotulo, _) in ORDENACOES.items()]
OPCOES_FAIXA = [(chave, rotulo) for chave, (rotulo, _, _) in FAIXAS.items()]


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
        faixa = params.get("faixa", "")
        ordem = params.get("ordem", ORDEM_PADRAO)
        return cls(
            departamentos=tuple(params.getlist("depto")),
            subdepartamentos=tuple(params.getlist("sub")),
            animais=tuple(params.getlist("animal")),
            marcas=tuple(params.getlist("marca")),
            faixa=faixa if faixa in FAIXAS else "",
            somente_ofertas=params.get("promo") == "1",
            ordem=ordem if ordem in ORDENACOES else ORDEM_PADRAO,
        )

    @property
    def ativos(self) -> bool:
        return bool(
            self.departamentos or self.subdepartamentos or self.animais or self.marcas
            or self.faixa or self.somente_ofertas
        )


@dataclass(frozen=True)
class OpcoesFiltro:
    departamentos: QuerySet
    subdepartamentos: QuerySet
    animais: QuerySet
    marcas: list[str]


@dataclass(frozen=True)
class EntradaMenu:
    departamento: Departamento
    subdepartamentos: list[Subdepartamento]


@dataclass(frozen=True)
class ItemMenu:
    categoria: Categoria
    departamentos: list[EntradaMenu]


def produtos_ativos() -> QuerySet[Produto]:
    return (
        Produto.objects.filter(ativo=True)
        .select_related("categoria", "departamento")
        .annotate(valor=Coalesce("preco_promocional", "preco"))
    )


def filtrar(produtos: QuerySet[Produto], filtros: FiltrosListagem) -> QuerySet[Produto]:
    if filtros.departamentos:
        produtos = produtos.filter(departamento__slug__in=filtros.departamentos)
    if filtros.subdepartamentos:
        produtos = produtos.filter(subdepartamento__slug__in=filtros.subdepartamentos)
    if filtros.animais:
        produtos = produtos.filter(categoria__slug__in=filtros.animais)
    if filtros.marcas:
        produtos = produtos.filter(marca__in=filtros.marcas)
    if filtros.somente_ofertas:
        produtos = produtos.filter(preco_promocional__isnull=False)
    if filtros.faixa:
        _, minimo, maximo = FAIXAS[filtros.faixa]
        if minimo is not None:
            produtos = produtos.filter(valor__gte=minimo)
        if maximo is not None:
            produtos = produtos.filter(valor__lt=maximo)
    return produtos


def ordenar(produtos: QuerySet[Produto], ordem: str) -> QuerySet[Produto]:
    return produtos.order_by(ORDENACOES[ordem][1], "nome")


def opcoes_de_filtro(base: QuerySet[Produto], filtros: FiltrosListagem) -> OpcoesFiltro:
    departamentos = Departamento.objects.filter(pk__in=base.values("departamento"))
    escopo = filtros.departamentos or (
        [d.slug for d in departamentos] if len(departamentos) == 1 else []
    )
    subdepartamentos = Subdepartamento.objects.filter(
        pk__in=base.values("subdepartamento"), departamento__slug__in=escopo,
    )
    return OpcoesFiltro(
        departamentos=departamentos,
        subdepartamentos=subdepartamentos,
        animais=Categoria.objects.filter(pk__in=base.values("categoria")),
        marcas=sorted(set(base.exclude(marca="").values_list("marca", flat=True))),
    )


def buscar(termo: str) -> QuerySet[Produto]:
    produtos = produtos_ativos()
    return produtos.filter(texto_busca__contains=normalizar(termo)) if termo else produtos


def sugerir(termo: str, limite: int = 6) -> list[Produto]:
    return list(produtos_ativos().filter(texto_busca__contains=normalizar(termo)).order_by("-vendas")[:limite])


def produtos_em_oferta() -> QuerySet[Produto]:
    return produtos_ativos().filter(preco_promocional__isnull=False)


def mais_vendidos(limite: int) -> list[Produto]:
    return list(produtos_ativos().order_by("-vendas")[:limite])


def ofertas(limite: int) -> list[Produto]:
    return list(produtos_em_oferta().order_by("-vendas")[:limite])


def destaques_por_animal(animais: int, limite: int) -> list[tuple[Categoria, list[Produto]]]:
    secoes = []
    for categoria in Categoria.objects.all():
        itens = list(produtos_ativos().filter(categoria=categoria).order_by("-vendas")[:limite])
        if itens:
            secoes.append((categoria, itens))
    return secoes[:animais]


def marcas_disponiveis() -> list[str]:
    return sorted(set(produtos_ativos().exclude(marca="").values_list("marca", flat=True)))


def relacionados(produto: Produto, limite: int = 10) -> list[Produto]:
    return list(
        produtos_ativos()
        .filter(Q(departamento=produto.departamento) | Q(categoria=produto.categoria))
        .exclude(pk=produto.pk)
        .order_by("-vendas")[:limite]
    )


def menu_por_animal() -> list[ItemMenu]:
    combinacoes = (
        Produto.objects.filter(ativo=True, departamento__isnull=False)
        .values_list("categoria_id", "departamento_id", "subdepartamento_id")
        .distinct()
    )
    subs_por_animal: dict[int, dict[int, set[int]]] = {}
    for categoria_id, departamento_id, subdepartamento_id in combinacoes:
        subs = subs_por_animal.setdefault(categoria_id, {}).setdefault(departamento_id, set())
        if subdepartamento_id:
            subs.add(subdepartamento_id)

    departamentos = list(Departamento.objects.all())
    subdepartamentos = list(Subdepartamento.objects.all())
    return [
        ItemMenu(
            categoria=categoria,
            departamentos=[
                EntradaMenu(
                    departamento=departamento,
                    subdepartamentos=[s for s in subdepartamentos if s.pk in subs_por_animal[categoria.pk][departamento.pk]],
                )
                for departamento in departamentos
                if departamento.pk in subs_por_animal.get(categoria.pk, {})
            ],
        )
        for categoria in Categoria.objects.all()
    ]


def par_caes_e_gatos() -> tuple[Categoria, Categoria] | None:
    animais = {c.slug: c for c in Categoria.objects.filter(slug__in=["caes", "gatos"])}
    return (animais["caes"], animais["gatos"]) if len(animais) == 2 else None
