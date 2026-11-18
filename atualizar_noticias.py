"""Robô de manchetes: lê os RSS de fontes-noticias.txt e grava noticias-auto.json (só título, fonte, link e horário).
Roda sozinho no GitHub a cada 30 minutos (.github/workflows/noticias.yml). Usa só a biblioteca padrão do Python."""
import json, re, sys, urllib.request, html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

RAIZ = Path(__file__).resolve().parent
MAX_POR_FONTE, MAX_TOTAL = 10, 30

def ler_fontes():
    fontes = []
    for linha in (RAIZ / "fontes-noticias.txt").read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "|" not in linha:
            continue
        nome, url = [p.strip() for p in linha.split("|", 1)]
        fontes.append((nome, url))
    return fontes

def data_iso(txt):
    if not txt:
        return None
    txt = txt.strip()
    for f in (parsedate_to_datetime, lambda t: datetime.fromisoformat(t.replace("Z", "+00:00"))):
        try:
            d = f(txt)
            return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return None

def limpar(t):
    t = html.unescape(re.sub(r"<[^>]+>", "", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def ler_feed(nome, url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (TV corporativa; leitor RSS)"})
    raiz = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
    itens = []
    for it in raiz.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        filho = {c.tag.split("}")[-1]: c for c in it}
        titulo = limpar(filho["title"].text if "title" in filho else "")
        link = ""
        if "link" in filho:
            link = (filho["link"].text or filho["link"].get("href") or "").strip()
        quando = None
        for k in ("pubDate", "published", "updated", "date"):
            if k in filho:
                quando = data_iso(filho[k].text)
                if quando:
                    break
        if titulo and len(titulo) > 15:
            itens.append({"titulo": titulo, "fonte": nome, "link": link, "quando": quando})
        if len(itens) >= MAX_POR_FONTE:
            break
    return itens

def main():
    todos, vistos, log = [], set(), []
    for nome, url in ler_fontes():
        try:
            itens = ler_feed(nome, url)
            log.append(f"OK   {nome}: {len(itens)}")
        except Exception as e:
            log.append(f"ERRO {nome}: {e}")
            continue
        for i in itens:
            chave = re.sub(r"\W+", "", i["titulo"].lower())[:80]
            if chave not in vistos:
                vistos.add(chave)
                todos.append(i)
    todos.sort(key=lambda i: i["quando"] or "", reverse=True)
    print("\n".join(log))
    if not todos:
        print("Nenhuma manchete obtida; arquivo anterior mantido.")
        return 0
    saida = {"gerado": datetime.now(timezone.utc).isoformat(), "itens": todos[:MAX_TOTAL]}
    (RAIZ / "noticias-auto.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(saida['itens'])} manchetes gravadas.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
