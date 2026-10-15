import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "desconhecido") if request else "desconhecido"


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    logger.info("login_ok usuario=%s ip=%s", user.pk, _ip(request))


@receiver(user_login_failed)
def registrar_login_falho(sender, credentials, request=None, **kwargs):
    logger.warning("login_falhou ip=%s", _ip(request))


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    if user is not None:
        logger.info("logout usuario=%s", user.pk)
