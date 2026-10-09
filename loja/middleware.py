import logging

from django.shortcuts import render

from .backoffice.erros import BackofficeIndisponivel

logger = logging.getLogger(__name__)


class BackofficeIndisponivelMiddleware:
    """Mostra uma página de manutenção quando o backoffice não responde e não há cópia do catálogo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, BackofficeIndisponivel):
            return None
        logger.error("site_sem_backoffice caminho=%s", request.path)
        resposta = render(request, "loja/indisponivel.html", status=503)
        resposta["Retry-After"] = "30"
        return resposta
