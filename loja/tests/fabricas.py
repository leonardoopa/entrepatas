from decimal import Decimal

from django.contrib.auth import get_user_model

from loja.models import Categoria, Departamento, Produto, Subdepartamento

DADOS_ENTREGA = {
    "nome": "Ana", "email": "ana@example.com", "telefone": "",
    "cep": "01001-000", "endereco": "Rua A, 1", "cidade": "São Paulo", "uf": "sp",
}
SENHA = "Senha!Forte123"


def criar_catalogo():
    caes = Categoria.objects.create(nome="Cães", slug="caes", emoji="🐶")
    gatos = Categoria.objects.create(nome="Gatos", slug="gatos", emoji="🐱")
    racoes = Departamento.objects.create(nome="Rações", slug="racoes")
    brinquedos = Departamento.objects.create(nome="Brinquedos", slug="brinquedos")
    seca = Subdepartamento.objects.create(departamento=racoes, nome="Ração Seca", slug="racao-seca")
    umida = Subdepartamento.objects.create(departamento=racoes, nome="Ração Úmida", slug="racao-umida", ordem=1)
    produtos = {
        "racao": Produto.objects.create(
            categoria=caes, departamento=racoes, subdepartamento=seca, nome="Ração", slug="racao", marca="X",
            preco=Decimal("100.00"), preco_promocional=Decimal("80.00"), estoque=5, vendas=10,
        ),
        "bola": Produto.objects.create(
            categoria=caes, departamento=brinquedos, nome="Bola", slug="bola", marca="Y",
            preco=Decimal("30.00"), estoque=50, vendas=99,
        ),
        "racao_gato": Produto.objects.create(
            categoria=gatos, departamento=racoes, subdepartamento=umida, nome="Ração Gato", slug="racao-gato", marca="X",
            preco=Decimal("250.00"), estoque=9,
        ),
        "osso": Produto.objects.create(
            categoria=caes, departamento=brinquedos, nome="Osso", slug="osso",
            preco=Decimal("10.00"), estoque=0,
        ),
    }
    return {
        "caes": caes, "gatos": gatos, "racoes": racoes, "brinquedos": brinquedos,
        "seca": seca, "umida": umida, **produtos,
    }


def criar_usuario(email="ana@example.com", nome="Ana", senha=SENHA):
    return get_user_model().objects.create_user(username=email, email=email, password=senha, first_name=nome)
