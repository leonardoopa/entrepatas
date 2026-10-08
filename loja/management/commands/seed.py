from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from loja.models import Categoria, Produto

CATEGORIAS = [
    ("Cães", "🐶"),
    ("Gatos", "🐱"),
    ("Pássaros", "🐦"),
    ("Peixes", "🐟"),
    ("Farmácia", "💊"),
    ("Higiene", "🛁"),
]

# (categoria, nome, marca, preço, promocional, estoque, destaque)
PRODUTOS = [
    ("Cães", "Ração Premium Adultos 15kg", "NutriPet", "189.90", "159.90", 25, True),
    ("Cães", "Ração Filhotes Frango 10kg", "NutriPet", "139.90", None, 18, True),
    ("Cães", "Bolinha de Borracha", "PataFeliz", "19.90", None, 80, False),
    ("Cães", "Coleira Ajustável M", "PataFeliz", "34.90", "27.90", 40, False),
    ("Gatos", "Ração Gatos Castrados 10kg", "MiauMix", "169.90", None, 20, True),
    ("Gatos", "Areia Higiênica 4kg", "MiauMix", "24.90", "19.90", 60, True),
    ("Gatos", "Arranhador Torre", "PataFeliz", "129.90", None, 8, False),
    ("Pássaros", "Mistura de Sementes 500g", "AsaLeve", "14.90", None, 50, False),
    ("Peixes", "Ração para Peixes Tropicais 100g", "AquaVida", "12.90", None, 70, False),
    ("Farmácia", "Antipulgas Cães até 10kg", "VetCare", "79.90", "64.90", 30, True),
    ("Higiene", "Shampoo Neutro 500ml", "BanhoBom", "29.90", None, 45, False),
    ("Higiene", "Tapete Higiênico 30un", "BanhoBom", "74.90", "59.90", 0, False),
]


class Command(BaseCommand):
    help = "Popula o banco com categorias e produtos de exemplo (idempotente)."

    def handle(self, *args, **options):
        cats = {}
        for ordem, (nome, emoji) in enumerate(CATEGORIAS):
            cats[nome], _ = Categoria.objects.update_or_create(
                slug=slugify(nome), defaults={"nome": nome, "emoji": emoji, "ordem": ordem}
            )
        for cat, nome, marca, preco, promo, estoque, destaque in PRODUTOS:
            Produto.objects.update_or_create(
                slug=slugify(nome),
                defaults={
                    "categoria": cats[cat], "nome": nome, "marca": marca,
                    "descricao": f"{nome} da marca {marca}.",
                    "preco": Decimal(preco),
                    "preco_promocional": Decimal(promo) if promo else None,
                    "estoque": estoque, "destaque": destaque, "ativo": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(
            f"{Categoria.objects.count()} categorias, {Produto.objects.count()} produtos."
        ))
