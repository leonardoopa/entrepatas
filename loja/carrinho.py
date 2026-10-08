from decimal import Decimal

from django.conf import settings

from .models import Produto

SESSION_KEY = "carrinho"


class Carrinho:
    """Carrinho guardado na sessão: {produto_id: quantidade}."""

    def __init__(self, request):
        self.session = request.session
        self.itens = self.session.get(SESSION_KEY, {})

    def _salvar(self):
        self.session[SESSION_KEY] = self.itens

    def definir(self, produto, quantidade):
        quantidade = min(int(quantidade), produto.estoque)
        if quantidade <= 0:
            self.itens.pop(str(produto.pk), None)
        else:
            self.itens[str(produto.pk)] = quantidade
        self._salvar()

    def adicionar(self, produto, quantidade=1):
        atual = self.itens.get(str(produto.pk), 0)
        self.definir(produto, atual + quantidade)

    def remover(self, produto):
        self.itens.pop(str(produto.pk), None)
        self._salvar()

    def limpar(self):
        self.itens = {}
        self.session.pop(SESSION_KEY, None)

    def linhas(self):
        """Lista de (produto, quantidade, subtotal) para itens ainda ativos."""
        produtos = Produto.objects.filter(pk__in=self.itens.keys(), ativo=True)
        return [
            (p, self.itens[str(p.pk)], p.preco_final * self.itens[str(p.pk)])
            for p in produtos
        ]

    def __len__(self):
        return sum(self.itens.values())

    @staticmethod
    def calcular(linhas):
        """Totais de um conjunto de linhas: subtotal, frete, total e quanto falta para frete grátis."""
        subtotal = sum((s for _, _, s in linhas), Decimal("0"))
        gratis = subtotal >= settings.FRETE_GRATIS_ACIMA
        frete = Decimal("0") if gratis or not linhas else settings.FRETE_FIXO
        return {
            "subtotal": subtotal,
            "frete": frete,
            "total": subtotal + frete,
            "frete_gratis": gratis,
            "falta_frete": max(settings.FRETE_GRATIS_ACIMA - subtotal, Decimal("0")),
            "progresso_frete": int(min(subtotal / settings.FRETE_GRATIS_ACIMA, 1) * 100),
        }
