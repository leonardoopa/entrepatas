import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageOps

from loja.cena import EXTENSOES_FOTO, PASTA_FOTOS_NO_DISCO

logger = logging.getLogger(__name__)

TAMANHO_PADRAO = 320
CENTRO_DO_CORTE = (0.5, 0.3)
QUALIDADE_WEBP = 82


class Command(BaseCommand):
    help = "Recorta em quadrado, reduz e converte para WebP as fotos usadas na cena da home."

    def add_arguments(self, parser):
        parser.add_argument("origem", type=Path, help="Pasta com as fotos originais.")
        parser.add_argument("animal", choices=["caes", "gatos"])
        parser.add_argument("--tamanho", type=int, default=TAMANHO_PADRAO, help="Lado do quadrado em pixels.")
        parser.add_argument("--destino", type=Path, default=PASTA_FOTOS_NO_DISCO, help="Pasta base de destino.")

    def handle(self, *args, origem: Path, animal: str, tamanho: int, destino: Path, **options):
        if not origem.is_dir():
            raise CommandError(f"Pasta não encontrada: {origem}")
        fotos = sorted(f for f in origem.iterdir() if f.suffix.lower() in EXTENSOES_FOTO)
        if not fotos:
            raise CommandError(f"Nenhuma foto (jpg, png ou webp) em {origem}")

        pasta = destino / animal
        pasta.mkdir(parents=True, exist_ok=True)
        for anterior in pasta.glob(f"{animal}-*.webp"):
            anterior.unlink()
        for indice, foto in enumerate(fotos, start=1):
            self._converter(foto, pasta / f"{animal}-{indice:02d}.webp", tamanho)

        mensagem = f"{len(fotos)} fotos de {animal} salvas em {pasta}"
        logger.info("fotos_cena_preparadas animal=%s quantidade=%d", animal, len(fotos))
        self.stdout.write(self.style.SUCCESS(mensagem))

    @staticmethod
    def _converter(origem: Path, destino: Path, tamanho: int) -> None:
        with Image.open(origem) as imagem:
            imagem = ImageOps.exif_transpose(imagem).convert("RGB")
            lado = min(tamanho, *imagem.size)
            quadrada = ImageOps.fit(imagem, (lado, lado), Image.LANCZOS, centering=CENTRO_DO_CORTE)
            quadrada.save(destino, "WEBP", quality=QUALIDADE_WEBP)
