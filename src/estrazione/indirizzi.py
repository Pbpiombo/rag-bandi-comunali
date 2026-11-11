"""Forma canonica degli URL, usata ovunque un URL viene salvato o confrontato."""

import re
from urllib.parse import urlsplit, urlunsplit

# Parametri che dicono da dove arriva il visitatore, non quale pagina e'
TRACCIAMENTO = re.compile(
    r"^(utm_[a-z]+|fbclid|gclid|dclid|msclkid|yclid|mc_cid|mc_eid|_ga|_gl)$",
    re.IGNORECASE,
)


def url_canonico(url: str) -> str:
    """Riduce un URL alla forma con cui viene salvato e confrontato.

    Schema https, dominio in minuscolo, niente barra finale, niente
    frammento (#...), niente parametri di tracciamento. Gli altri
    parametri restano, nell'ordine e nella codifica originali, perche'
    possono identificare la pagina (es. ?id=123).
    """
    parti = urlsplit(url.strip())

    percorso = parti.path.rstrip("/")

    parametri = [
        p
        for p in parti.query.split("&")
        if p and not TRACCIAMENTO.match(p.split("=", 1)[0])
    ]

    return urlunsplit(
        ("https", parti.netloc.lower(), percorso, "&".join(parametri), "")
    )
