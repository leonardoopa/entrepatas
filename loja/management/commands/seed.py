import logging
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from loja.models import Categoria, Departamento, Produto, Subdepartamento

from ._catalogo_demo import ANIMAIS, DEPARTAMENTOS, PRODUTOS, SUBDEPARTAMENTOS, TEXTOS, ProdutoDemo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Popula o banco com o catálogo fictício de demonstração (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar", action="store_true",
            help="Apaga antes produtos nunca vendidos que não fazem parte do catálogo de demonstração "
                 "(inclusive os cadastrados no admin) e categorias e departamentos vazios.",
        )

    def handle(self, *args, **options):
        animais = self._salvar_animais()
        departamentos = self._salvar_departamentos()
        subdepartamentos = self._salvar_subdepartamentos(departamentos)
        slugs = [self._salvar_produto(item, animais, departamentos, subdepartamentos) for item in PRODUTOS]
        if options["limpar"]:
            self._limpar(slugs, animais, departamentos, subdepartamentos)

        resumo = (
            f"{Categoria.objects.count()} animais, {Departamento.objects.count()} departamentos, "
            f"{Subdepartamento.objects.count()} subdepartamentos, {Produto.objects.count()} produtos."
        )
        logger.info("seed_concluido %s", resumo)
        self.stdout.write(self.style.SUCCESS(resumo))

    def _salvar_animais(self) -> dict[str, Categoria]:
        return {
            slugify(nome): Categoria.objects.update_or_create(
                slug=slugify(nome), defaults={"nome": nome, "emoji": emoji, "ordem": ordem}
            )[0]
            for ordem, (nome, emoji) in enumerate(ANIMAIS)
        }

    def _salvar_departamentos(self) -> dict[str, Departamento]:
        return {
            slug: Departamento.objects.update_or_create(slug=slug, defaults={"nome": nome, "ordem": ordem})[0]
            for ordem, (slug, nome) in enumerate(DEPARTAMENTOS.items())
        }

    def _salvar_subdepartamentos(self, departamentos) -> dict[str, Subdepartamento]:
        return {
            slug: Subdepartamento.objects.update_or_create(
                slug=slug, defaults={"departamento": departamentos[departamento], "nome": nome, "ordem": ordem},
            )[0]
            for departamento, itens in SUBDEPARTAMENTOS.items()
            for ordem, (slug, nome) in enumerate(itens)
        }

    def _salvar_produto(self, item: ProdutoDemo, animais, departamentos, subdepartamentos) -> str:
        slug = slugify(item.nome)
        sorteio = random.Random(slug)
        Produto.objects.update_or_create(
            slug=slug,
            defaults={
                "categoria": animais[item.animal],
                "departamento": departamentos[item.departamento],
                "subdepartamento": subdepartamentos[item.subdepartamento],
                "nome": item.nome,
                "marca": item.marca,
                "descricao": f"{item.nome}, da {item.marca}. {TEXTOS[item.departamento]}",
                "preco": Decimal(item.preco),
                "preco_promocional": Decimal(item.promocional) if item.promocional else None,
                "estoque": item.estoque,
                "tipo": item.tipo,
                "cor": item.cor,
                "avaliacao": Decimal(str(round(sorteio.uniform(3.9, 5.0), 1))),
                "num_avaliacoes": sorteio.randint(8, 480),
                "vendas": sorteio.randint(300, 900) if item.destaque else sorteio.randint(5, 300),
                "destaque": item.destaque,
                "ativo": True,
            },
        )
        return slug

    def _limpar(self, slugs, animais, departamentos, subdepartamentos) -> None:
        removidos, _ = Produto.objects.exclude(slug__in=slugs).filter(itempedido__isnull=True).delete()
        Categoria.objects.exclude(slug__in=animais).filter(produtos__isnull=True).delete()
        Subdepartamento.objects.exclude(slug__in=subdepartamentos).filter(produtos__isnull=True).delete()
        Departamento.objects.exclude(slug__in=departamentos).filter(produtos__isnull=True).delete()
        logger.warning("seed_limpeza produtos_removidos=%d", removidos)
