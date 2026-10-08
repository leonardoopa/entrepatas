"""Catálogo fictício para demonstração. Marcas, produtos e avaliações são inventados."""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from loja.models import Categoria, Departamento, Produto

ANIMAIS = [("Cães", "🐶"), ("Gatos", "🐱"), ("Pássaros", "🐦"), ("Peixes", "🐟"), ("Roedores", "🐹")]

DEPARTAMENTOS = {
    "racoes": "Rações",
    "petiscos": "Petiscos e Ossos",
    "higiene": "Higiene e Beleza",
    "farmacia": "Farmácia",
    "brinquedos": "Brinquedos",
    "coleiras": "Coleiras, Guias e Peitorais",
    "comedouros": "Comedouros e Bebedouros",
    "camas": "Camas e Casinhas",
    "transporte": "Transporte",
}

TEXTOS = {
    "racoes": "Alimento completo e balanceado, com proteínas de qualidade, vitaminas e minerais para o dia a dia. "
              "Siga a tabela de porções da embalagem e mantenha água fresca sempre disponível.",
    "petiscos": "Petisco saboroso para premiar e fortalecer o vínculo com seu pet. "
                "Ofereça como complemento, sem substituir a refeição principal.",
    "brinquedos": "Diversão garantida para gastar energia e estimular o instinto natural. "
                  "Material resistente e seguro. Supervisione as brincadeiras.",
    "higiene": "Cuidado e conforto para a rotina de limpeza do seu pet. "
               "Fórmula suave, indicada para uso frequente.",
    "farmacia": "Produto de uso veterinário. Siga a orientação do médico-veterinário e as instruções da bula.",
    "coleiras": "Acessório pensado para o conforto e a segurança nos passeios, com acabamento reforçado e ajuste fácil.",
    "comedouros": "Alimentação e hidratação com praticidade e higiene. Material resistente e fácil de limpar.",
    "transporte": "Segurança e conforto para levar seu pet ao veterinário, a passeios e viagens.",
    "camas": "Espaço macio e aconchegante para o descanso do seu pet, com tecido de fácil limpeza.",
}

# (animal, departamento, nome, marca, preço, promocional, tipo, cor, estoque, destaque)
PRODUTOS = [
    # Cães
    ("caes", "racoes", "Ração Premium Adultos Frango e Arroz 15kg", "NutriPet", "219.90", "189.90", "saco", "#D96C4A", 40, True),
    ("caes", "racoes", "Ração Filhotes Raças Pequenas 3kg", "NutriPet", "69.90", None, "saco", "#F2B544", 35, False),
    ("caes", "racoes", "Ração Sênior 7+ Frango 10kg", "Natu Pet", "159.90", "139.90", "saco", "#4F9D69", 22, True),
    ("caes", "racoes", "Ração Light Controle de Peso 10kg", "Natu Pet", "149.90", None, "saco", "#7B6BB3", 18, False),
    ("caes", "racoes", "Alimento Úmido Carne ao Molho 280g", "Focinho Feliz", "7.90", None, "lata", "#9A6B3F", 120, False),
    ("caes", "racoes", "Alimento Úmido Frango com Legumes 280g", "Focinho Feliz", "7.90", "6.90", "lata", "#D8688C", 110, False),
    ("caes", "petiscos", "Osso Natural Mini 100g", "Mordida Boa", "29.90", "24.90", "osso", "#F2B544", 60, True),
    ("caes", "petiscos", "Bifinho Sabor Carne 500g", "Mordida Boa", "24.90", None, "saco", "#C8453B", 70, False),
    ("caes", "petiscos", "Biscoito Dental Cuidado Oral 7un", "Focinho Feliz", "18.90", None, "caixa", "#4F9D69", 45, False),
    ("caes", "petiscos", "Palito Mastigável Frango 10un", "Mordida Boa", "32.90", "27.90", "osso", "#9A6B3F", 38, False),
    ("caes", "brinquedos", "Bolinha de Borracha Maciça", "Pata Feliz", "19.90", None, "bola", "#F2B544", 80, True),
    ("caes", "brinquedos", "Corda com Nós Trançada", "Pata Feliz", "24.90", "19.90", "osso", "#4A90D9", 55, False),
    ("caes", "brinquedos", "Mordedor Osso Resistente G", "Pata Feliz", "39.90", None, "osso", "#D96C4A", 30, False),
    ("caes", "brinquedos", "Pelúcia Camarão com Apito", "Bicho Chic", "49.90", "44.90", "bola", "#D8688C", 25, False),
    ("caes", "brinquedos", "Frisbee Flexível", "Bicho Chic", "29.90", None, "bola", "#2E9CA6", 42, False),
    ("caes", "higiene", "Shampoo Neutro Pelos Claros 500ml", "Banho Bom", "29.90", None, "frasco", "#4A90D9", 48, False),
    ("caes", "higiene", "Condicionador Hidratante 500ml", "Banho Bom", "32.90", "27.90", "frasco", "#D8688C", 33, False),
    ("caes", "higiene", "Tapete Higiênico 30un", "Banho Bom", "74.90", "59.90", "caixa", "#2E9CA6", 0, False),
    ("caes", "higiene", "Escova Removedora de Pelos", "Bicho Chic", "39.90", None, "caixa", "#7B6BB3", 27, False),
    ("caes", "farmacia", "Antipulgas e Carrapatos até 10kg", "VetCare", "89.90", "74.90", "caixa", "#C8453B", 30, True),
    ("caes", "farmacia", "Vermífugo 4 Comprimidos", "VetCare", "54.90", None, "caixa", "#2E9CA6", 26, False),
    ("caes", "farmacia", "Suplemento Articulações 60 Comprimidos", "VetCare", "119.90", "99.90", "frasco", "#7B6BB3", 15, False),
    ("caes", "coleiras", "Coleira Ajustável M", "Pata Feliz", "34.90", "27.90", "coleira", "#17375E", 40, False),
    ("caes", "coleiras", "Peitoral Passeio Confort G", "Bicho Chic", "79.90", "69.90", "coleira", "#D96C4A", 24, False),
    ("caes", "coleiras", "Guia Retrátil 5m", "Bicho Chic", "69.90", None, "coleira", "#4F9D69", 19, False),
    ("caes", "comedouros", "Comedouro Inox Antiderrapante", "Pata Feliz", "44.90", None, "pote", "#9A9FAA", 36, False),
    ("caes", "comedouros", "Bebedouro Portátil para Passeio 500ml", "Pata Feliz", "39.90", None, "pote", "#2E9CA6", 33, False),
    ("caes", "transporte", "Caixa de Transporte Nº 3", "Casa Pet", "169.90", "149.90", "caixa", "#17375E", 14, False),
    ("caes", "camas", "Cama Redonda Pelúcia M", "Casa Pet", "149.90", "129.90", "cama", "#F2B544", 14, True),
    ("caes", "camas", "Cama Retangular Ortopédica G", "Casa Pet", "239.90", None, "cama", "#17375E", 9, False),
    ("caes", "camas", "Casinha Plástica Pequena", "Casa Pet", "199.90", None, "cama", "#7B6BB3", 11, False),
    # Gatos
    ("gatos", "racoes", "Ração Gatos Castrados Salmão 10kg", "Miau Mix", "179.90", "159.90", "saco", "#4A90D9", 28, True),
    ("gatos", "racoes", "Ração Filhotes Frango 3kg", "Miau Mix", "74.90", None, "saco", "#F2B544", 31, False),
    ("gatos", "racoes", "Ração Gatos Adultos Peixes 10kg", "Miau Mix", "169.90", None, "saco", "#2E9CA6", 20, False),
    ("gatos", "racoes", "Sachê Atum ao Molho 85g", "Focinho Feliz", "3.90", None, "lata", "#D8688C", 200, False),
    ("gatos", "racoes", "Ração Sênior 7+ 3kg", "Natu Pet", "84.90", "74.90", "saco", "#4F9D69", 17, False),
    ("gatos", "petiscos", "Petisco Cremoso Atum 4un", "Miau Mix", "12.90", None, "caixa", "#4A90D9", 90, False),
    ("gatos", "petiscos", "Biscoito Crocante Frango 60g", "Miau Mix", "9.90", None, "caixa", "#F2B544", 85, False),
    ("gatos", "petiscos", "Erva-de-Gato Natural 30g", "Natu Pet", "14.90", None, "frasco", "#4F9D69", 50, False),
    ("gatos", "brinquedos", "Varinha com Penas", "Bicho Chic", "22.90", None, "bola", "#D8688C", 46, False),
    ("gatos", "brinquedos", "Ratinho de Pelúcia com Catnip", "Bicho Chic", "14.90", None, "bola", "#7B6BB3", 75, False),
    ("gatos", "brinquedos", "Arranhador Torre 3 Andares", "Pata Feliz", "229.90", "199.90", "caixa", "#9A6B3F", 8, True),
    ("gatos", "higiene", "Areia Higiênica Grãos Finos 4kg", "Pipi Clean", "24.90", "19.90", "saco", "#F2B544", 150, True),
    ("gatos", "higiene", "Areia Sílica Perfumada 3,8kg", "Pipi Clean", "39.90", None, "saco", "#2E9CA6", 64, False),
    ("gatos", "higiene", "Shampoo a Seco Gatos 150ml", "Banho Bom", "27.90", None, "frasco", "#7B6BB3", 29, False),
    ("gatos", "farmacia", "Antipulgas Gatos até 4kg", "VetCare", "79.90", "67.90", "caixa", "#C8453B", 21, False),
    ("gatos", "farmacia", "Pasta Maltes para Bolas de Pelo 30g", "VetCare", "32.90", None, "frasco", "#4F9D69", 34, False),
    ("gatos", "coleiras", "Coleira com Guizo", "Pata Feliz", "17.90", None, "coleira", "#D8688C", 58, False),
    ("gatos", "comedouros", "Fonte Bebedouro 2L", "Casa Pet", "189.90", "159.90", "pote", "#4A90D9", 12, False),
    ("gatos", "transporte", "Caixa de Transporte M", "Casa Pet", "129.90", None, "caixa", "#17375E", 16, False),
    ("gatos", "comedouros", "Comedouro Duplo Cerâmica", "Casa Pet", "54.90", None, "pote", "#D8688C", 20, False),
    ("gatos", "camas", "Cama Iglu Pelúcia", "Casa Pet", "119.90", None, "cama", "#D8688C", 13, False),
    ("gatos", "camas", "Almofada Cobertor Soft", "Casa Pet", "89.90", "74.90", "cama", "#4A90D9", 23, False),
    # Pássaros
    ("passaros", "racoes", "Mistura de Sementes Calopsita 500g", "Asa Leve", "14.90", None, "saco", "#F2B544", 52, False),
    ("passaros", "racoes", "Ração Extrusada Papagaio 600g", "Asa Leve", "38.90", "32.90", "saco", "#4F9D69", 26, False),
    ("passaros", "brinquedos", "Balanço com Sino", "Asa Leve", "16.90", None, "bola", "#D96C4A", 37, False),
    ("passaros", "comedouros", "Bebedouro Automático 120ml", "Asa Leve", "12.90", None, "pote", "#2E9CA6", 44, False),
    # Peixes
    ("peixes", "racoes", "Ração Flocos Tropicais 100g", "Aqua Vida", "12.90", None, "frasco", "#D96C4A", 70, False),
    ("peixes", "racoes", "Ração Granulada Bettas 30g", "Aqua Vida", "15.90", "12.90", "frasco", "#4A90D9", 66, False),
    ("peixes", "farmacia", "Condicionador de Água 120ml", "Aqua Vida", "21.90", None, "frasco", "#2E9CA6", 41, False),
    ("peixes", "farmacia", "Kit Teste de Qualidade da Água", "Aqua Vida", "59.90", None, "caixa", "#7B6BB3", 18, False),
    # Roedores
    ("roedores", "racoes", "Ração Hamster e Gerbil 500g", "ZooMix", "16.90", None, "saco", "#9A6B3F", 48, False),
    ("roedores", "racoes", "Feno Natural Coelhos e Porquinhos 500g", "ZooMix", "18.90", None, "saco", "#4F9D69", 39, False),
    ("roedores", "brinquedos", "Mordedor de Madeira", "ZooMix", "9.90", None, "osso", "#D96C4A", 62, False),
    ("roedores", "brinquedos", "Roda de Exercício Silenciosa", "ZooMix", "39.90", "34.90", "bola", "#17375E", 21, False),
]


class Command(BaseCommand):
    help = "Popula o banco com o catálogo fictício de demonstração (idempotente)."

    def handle(self, *args, **options):
        animais = {}
        for ordem, (nome, emoji) in enumerate(ANIMAIS):
            animais[slugify(nome)], _ = Categoria.objects.update_or_create(
                slug=slugify(nome), defaults={"nome": nome, "emoji": emoji, "ordem": ordem}
            )
        deptos = {}
        for ordem, (slug, nome) in enumerate(DEPARTAMENTOS.items()):
            deptos[slug], _ = Departamento.objects.update_or_create(
                slug=slug, defaults={"nome": nome, "ordem": ordem}
            )

        slugs = []
        for animal, depto, nome, marca, preco, promo, tipo, cor, estoque, destaque in PRODUTOS:
            slug = slugify(nome)
            slugs.append(slug)
            rng = random.Random(slug)  # avaliações estáveis entre execuções
            Produto.objects.update_or_create(
                slug=slug,
                defaults={
                    "categoria": animais[animal],
                    "departamento": deptos[depto],
                    "nome": nome,
                    "marca": marca,
                    "descricao": f"{nome}, da {marca}. {TEXTOS[depto]}",
                    "preco": Decimal(preco),
                    "preco_promocional": Decimal(promo) if promo else None,
                    "estoque": estoque,
                    "tipo": tipo,
                    "cor": cor,
                    "avaliacao": Decimal(str(round(rng.uniform(3.9, 5.0), 1))),
                    "num_avaliacoes": rng.randint(8, 480),
                    "vendas": rng.randint(300, 900) if destaque else rng.randint(5, 300),
                    "destaque": destaque,
                    "ativo": True,
                },
            )

        # Remove sobras de catálogos de demonstração antigos (só o que nunca foi vendido).
        Produto.objects.exclude(slug__in=slugs).filter(itempedido__isnull=True).delete()
        Categoria.objects.exclude(slug__in=animais).filter(produtos__isnull=True).delete()
        Departamento.objects.exclude(slug__in=deptos).filter(produtos__isnull=True).delete()

        self.stdout.write(self.style.SUCCESS(
            f"{Categoria.objects.count()} animais, {Departamento.objects.count()} departamentos, "
            f"{Produto.objects.count()} produtos."
        ))
