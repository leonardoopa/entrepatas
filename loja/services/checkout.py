import logging
import secrets
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from django.contrib.auth.models import AbstractBaseUser

from loja.dominio import NovoPedido, PedidoCriado
from loja.erros import (  # noqa: F401 — reexportados para quem usa o serviço
    CarrinhoVazio, CheckoutError, CheckoutIndisponivel, ItemIndisponivel, PedidoRecusado,
)
from loja.portas import PedidosRepositorio

from .carrinho import LinhaCarrinho
from .resumo import ResumoCompra

logger = logging.getLogger(__name__)


def novo_numero_pedido() -> str:
    return f"S{datetime.now():%y%m%d}-{secrets.token_hex(3).upper()}"


def _cliente(usuario: AbstractBaseUser | None, dados_entrega: Mapping[str, Any]) -> dict:
    if usuario is not None:
        return {"id_externo": str(usuario.pk), "nome": usuario.get_full_name() or dados_entrega["nome"], "email": usuario.email}
    email = str(dados_entrega["email"]).lower()
    return {
        "id_externo": f"visitante:{email}", "nome": dados_entrega["nome"], "email": email,
        "telefone": dados_entrega.get("telefone", ""),
    }


def finalizar_pedido(
    *,
    numero: str,
    dados_entrega: Mapping[str, Any],
    linhas: list[LinhaCarrinho],
    resumo: ResumoCompra,
    pedidos: PedidosRepositorio,
    usuario: AbstractBaseUser | None = None,
) -> PedidoCriado:
    if not linhas:
        raise CarrinhoVazio()
    pedido = NovoPedido(
        numero=numero,
        itens=tuple((linha.produto.sku, linha.quantidade) for linha in linhas),
        cliente=_cliente(usuario, dados_entrega),
        entrega={k: v for k, v in dados_entrega.items() if k in ("endereco", "cidade", "uf", "cep")},
        frete=resumo.frete,
    )
    try:
        criado = pedidos.criar(pedido)
    except ItemIndisponivel as erro:
        nomes = {linha.produto.sku: linha.produto.nome for linha in linhas}
        logger.warning("checkout_item_indisponivel sku=%s", erro.sku)
        raise ItemIndisponivel(erro.sku, nomes.get(erro.sku, "")) from erro
    except CheckoutError:
        logger.warning("checkout_recusado numero=%s", numero)
        raise
    logger.info(
        "pedido_criado numero=%s usuario=%s itens=%d total=%s repetido=%s",
        criado.numero, usuario.pk if usuario else "anonimo", len(linhas), criado.total, not criado.criado,
    )
    return criado
