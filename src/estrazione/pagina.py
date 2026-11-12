"""Scarica e ripulisce il testo di una pagina web."""

import html
import re
import urllib.request

INTESTAZIONI = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9",
}

# Blocchi da rimuovere per intero, contenuto compreso
BLOCCHI = ("script", "style", "noscript", "svg", "head")


def scarica(url: str, timeout: int = 30) -> str:
    """Scarica l'HTML grezzo di una pagina."""
    richiesta = urllib.request.Request(url, headers=INTESTAZIONI)
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        grezzo = risposta.read()

    return grezzo.decode("utf-8", errors="ignore")


def a_testo(html: str) -> str:
    """Estrae il testo leggibile dall'HTML.

    Non usa un parser completo: per il nostro scopo basta togliere i
    blocchi non testuali, sostituire i tag con a capo e ricomporre.
    """
    for blocco in BLOCCHI:
        html = re.sub(
            rf"<{blocco}\b.*?</{blocco}>",
            " ",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # I tag che chiudono un blocco diventano a capo, gli altri spazi
    html = re.sub(r"</(p|div|li|tr|h[1-6]|br)\s*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)

    testo = _entita(html)

    # Compatta gli spazi ma conserva la struttura in righe
    righe = [re.sub(r"[ \t]+", " ", r).strip() for r in testo.splitlines()]
    righe = [r for r in righe if r]

    return "\n".join(righe)


def _entita(testo: str) -> str:
    """Converte le entita' HTML piu' comuni."""
    sostituzioni = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
        "&egrave;": "è",
        "&eacute;": "é",
        "&agrave;": "à",
        "&igrave;": "ì",
        "&ograve;": "ò",
        "&ugrave;": "ù",
        "&euro;": "€",
        "&ndash;": "-",
        "&mdash;": "-",
    }

    for entita, carattere in sostituzioni.items():
        testo = testo.replace(entita, carattere)

    # Entita' numeriche: &#8364; -> €
    testo = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), testo)

    # Tutte le altre (&rsquo;, &ldquo;, &copy;, &Eacute;...), che la tabella
    # non conosce: le pagine del GAL MontagnAppennino le usano. La tabella
    # resta prima, cosi' il testo delle pagine che usano solo quelle (il
    # portale della Regione) non cambia: &nbsp; resta uno spazio normale e
    # &ndash; un trattino.
    return html.unescape(testo)


def ritaglia(testo: str) -> str:
    """Scarta le righe di navigazione conservando il contenuto.

    Una pagina istituzionale ha il contenuto utile in mezzo, circondato
    da menu e piè di pagina. Invece di scartare le righe brevi, che in un
    elenco puntato sono contenuto vero, si individua il blocco centrale
    ancorandolo alle righe lunghe.
    """
    righe = testo.splitlines()

    lunghe = [i for i, r in enumerate(righe) if len(r) >= 120]

    if not lunghe:
        return testo

    # Un margine attorno al blocco centrale, per non perdere gli elenchi
    # che precedono o seguono un paragrafo lungo
    inizio = max(0, lunghe[0] - 15)
    fine = min(len(righe), lunghe[-1] + 15)

    blocco = righe[inizio:fine]

    # Dentro il blocco, elimina solo le ripetizioni consecutive
    pulite = []
    for r in blocco:
        if not pulite or r != pulite[-1]:
            pulite.append(r)

    return "\n".join(pulite)


def prendi(url: str) -> str:
    """Scarica una pagina e ne restituisce il testo utile."""
    html = scarica(url)
    return ritaglia(a_testo(html))
