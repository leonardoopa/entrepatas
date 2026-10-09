from datetime import datetime
from decimal import Decimal
from typing import Any

from loja.dominio import (
    AnimalRef, DepartamentoRef, EntradaMenu, Facetas, ItemMenu, ItemPedidoSite, MarcaRef, Pagina, PedidoSite,
    ProdutoCatalogo, SubdepartamentoRef, Variacao, Vitrine,
)


def _animal(d: dict) -> AnimalRef:
    return AnimalRef(slug=d["slug"], nome=d["nome"], emoji=d.get("emoji", ""))


def _departamento(d: dict | None) -> DepartamentoRef | None:
    return None if d is None else DepartamentoRef(slug=d["slug"], nome=d["nome"])


def _subdepartamento(d: dict | None) -> SubdepartamentoRef | None:
    return None if d is None else SubdepartamentoRef(slug=d["slug"], nome=d["nome"], departamento=d.get("departamento", ""))


def _dinheiro(valor: Any) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def produto(d: dict) -> ProdutoCatalogo:
    grupo = d.get("grupo") or {}
    arte = d.get("arte") or {}
    return ProdutoCatalogo(
        sku=d["sku"],
        slug=d["slug"],
        nome=d["nome"],
        descricao=d.get("descricao", ""),
        marca=(d.get("marca") or {}).get("nome", ""),
        marca_slug=(d.get("marca") or {}).get("slug", ""),
        categoria=_animal(d["animal"]),
        departamento=_departamento(d.get("departamento")),
        subdepartamento=_subdepartamento(d.get("subdepartamento")),
        grupo=grupo.get("nome", ""),
        variacao=d.get("variacao", ""),
        preco=_dinheiro(d["preco"]),
        preco_promocional=_dinheiro(d.get("preco_promocional")),
        preco_final=_dinheiro(d["preco_final"]),
        estoque=int(d.get("estoque", 0)),
        avaliacao=_dinheiro(d.get("avaliacao", "0")),
        num_avaliacoes=int(d.get("num_avaliacoes", 0)),
        tipo=arte.get("tipo", "caixa"),
        cor=arte.get("cor", "#17375e"),
        imagens=tuple(d.get("imagens") or ()),
        promocao_fim=datetime.fromisoformat(d["promocao_fim"]) if d.get("promocao_fim") else None,
        variacoes=tuple(
            Variacao(
                sku=v["sku"], slug=v["slug"], rotulo=v.get("variacao", ""),
                preco_final=_dinheiro(v["preco_final"]), estoque=int(v.get("estoque", 0)),
            )
            for v in d.get("variacoes", ())
        ),
    )


def pagina(d: dict) -> Pagina:
    return Pagina(
        itens=tuple(produto(i) for i in d["itens"]),
        numero=d["pagina"], total_paginas=d["paginas"], total=d["total"],
    )


def facetas(d: dict) -> Facetas:
    return Facetas(
        animais=tuple(_animal(a) for a in d.get("animais", ())),
        departamentos=tuple(_departamento(x) for x in d.get("departamentos", ())),
        subdepartamentos=tuple(_subdepartamento(x) for x in d.get("subdepartamentos", ())),
        marcas=tuple(MarcaRef(slug=m["slug"], nome=m["nome"]) for m in d.get("marcas", ())),
    )


def menu(d: dict) -> list[ItemMenu]:
    return [
        ItemMenu(
            categoria=_animal(a),
            departamentos=tuple(
                EntradaMenu(
                    departamento=_departamento(dep),
                    subdepartamentos=tuple(_subdepartamento(s) for s in dep.get("subdepartamentos", ())),
                )
                for dep in a.get("departamentos", ())
            ),
        )
        for a in d.get("animais", ())
    ]


def vitrines(d: dict) -> dict[str, Vitrine]:
    return {
        codigo: Vitrine(codigo=codigo, nome=v["nome"], itens=tuple(produto(i) for i in v["itens"]))
        for codigo, v in d.items()
    }


def pedido(d: dict) -> PedidoSite:
    cliente = d.get("cliente") or {}
    return PedidoSite(
        numero=d["numero_externo"],
        status=d["status"],
        subtotal=_dinheiro(d["subtotal"]),
        frete=_dinheiro(d["frete"]),
        total=_dinheiro(d["total"]),
        comprado_em=datetime.fromisoformat(d["comprado_em"]),
        itens=tuple(
            ItemPedidoSite(
                sku=i["sku"], descricao=i["descricao"], quantidade=int(i["quantidade"]),
                preco_unitario=_dinheiro(i["preco_unitario"]),
            )
            for i in d.get("itens", ())
        ),
        cliente_id=cliente.get("id_externo", ""),
        nome=cliente.get("nome", ""),
        email=cliente.get("email", ""),
        entrega=d.get("entrega") or {},
    )
