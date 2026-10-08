import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def criar_usuario(*, nome: str, email: str, senha: str):
    usuario = get_user_model().objects.create_user(
        username=email, email=email, password=senha, first_name=nome,
    )
    logger.info("usuario_criado usuario=%s", usuario.pk)
    return usuario
