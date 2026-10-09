import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .erros import BackofficeIndisponivel, BackofficeNaoEncontrado, BackofficeRecusou

logger = logging.getLogger(__name__)

TENTATIVAS_DE_LEITURA = 2


def _sessao_com_repeticao() -> requests.Session:
    sessao = requests.Session()
    repeticao = Retry(
        total=TENTATIVAS_DE_LEITURA, backoff_factor=0.2, status_forcelist=(502, 503, 504), allowed_methods=("GET",),
    )
    sessao.mount("http://", HTTPAdapter(max_retries=repeticao))
    sessao.mount("https://", HTTPAdapter(max_retries=repeticao))
    return sessao


class ClienteBackoffice:
    """Fala com a API do backoffice. Só leituras são repetidas; pedidos nunca, para não duplicar."""

    def __init__(self, base_url: str, chave: str, timeout: float = 5.0, sessao: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.sessao = sessao or _sessao_com_repeticao()
        self.sessao.headers.update({"Authorization": f"Bearer {chave}", "Accept": "application/json"})

    def get(self, caminho: str, params: Any = None) -> dict:
        return self._enviar("GET", caminho, params=params)[1]

    def post(self, caminho: str, json: dict) -> tuple[int, dict]:
        return self._enviar("POST", caminho, json=json)

    def _enviar(self, metodo: str, caminho: str, **opcoes) -> tuple[int, dict]:
        url = f"{self.base_url}/{caminho.lstrip('/')}"
        try:
            resposta = self.sessao.request(metodo, url, timeout=self.timeout, **opcoes)
        except requests.RequestException as erro:
            logger.warning("backoffice_inacessivel metodo=%s caminho=%s erro=%s", metodo, caminho, type(erro).__name__)
            raise BackofficeIndisponivel(str(erro)) from erro

        if resposta.status_code >= 500:
            logger.warning("backoffice_erro_5xx metodo=%s caminho=%s status=%d", metodo, caminho, resposta.status_code)
            raise BackofficeIndisponivel(f"HTTP {resposta.status_code}")
        dados = self._corpo(resposta)
        if resposta.status_code == 404:
            raise BackofficeNaoEncontrado(caminho)
        if resposta.status_code >= 400:
            logger.warning("backoffice_recusou metodo=%s caminho=%s status=%d", metodo, caminho, resposta.status_code)
            raise BackofficeRecusou(resposta.status_code, dados)
        return resposta.status_code, dados

    @staticmethod
    def _corpo(resposta: requests.Response) -> dict:
        try:
            return resposta.json()
        except ValueError:
            return {}
