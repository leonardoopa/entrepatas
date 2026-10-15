class BackofficeErro(Exception):
    pass


class BackofficeIndisponivel(BackofficeErro):
    """Rede, tempo esgotado ou erro 5xx: vale tentar de novo mais tarde."""


class BackofficeNaoEncontrado(BackofficeErro):
    pass


class BackofficeRecusou(BackofficeErro):
    def __init__(self, status: int, dados: dict):
        super().__init__(f"O backoffice recusou a requisição ({status}): {dados.get('erro', '')}")
        self.status = status
        self.dados = dados
