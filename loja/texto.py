import unicodedata


def normalizar(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acentos.lower().split())
