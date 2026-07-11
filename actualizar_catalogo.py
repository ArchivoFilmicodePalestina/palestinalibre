#!/usr/bin/env python3
"""
Actualiza el catálogo cronológico multi-fuente (v2).

Fuentes definidas en fuentes.json:
  - "youtube": lista de canales (/videos) o playlists -> se extraen con yt-dlp
  - "manual":  entradas curadas a mano (Archive.org, videos sueltos, enlaces)

Uso:
    pip install yt-dlp
    python3 actualizar_catalogo.py
"""
import json, re, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).parent

def extraer_youtube(url):
    import os
    extra = os.environ.get("YTDLP_EXTRA", "").split()
    r = subprocess.run(
        ["yt-dlp", "--flat-playlist", *extra,
         "--print", "%(id)s|%(title)s|%(duration)s", url],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"⚠ yt-dlp falló con {url}:\n{r.stderr[-300:]}", file=sys.stderr)
        return []
    return [l for l in r.stdout.splitlines() if l.strip()]

def detectar_anio(titulo):
    """Devuelve (año, aproximado). Prioridad: (1947) > 1970s > último año suelto."""
    m = re.findall(r"\((1[89]\d{2}|20[0-2]\d)\)", titulo)
    if m:
        return int(m[-1]), False
    m = re.search(r"(1[89]\d{2}|20[0-2]\d)s", titulo)
    if m:
        return int(m.group(1)), True
    m = re.findall(r"(1[89]\d{2}|20[0-2]\d)", titulo)
    if m:
        return int(m[-1]), False
    m = re.search(r"años (\d{2})", titulo)
    if m:
        return 1900 + int(m.group(1)), True
    return None, True

def main():
    fuentes = json.loads((AQUI / "fuentes.json").read_text(encoding="utf-8"))
    items, sin_anio, vistos = [], [], set()

    # --- entradas manuales primero (tienen prioridad en el dedupe) ---
    for e in fuentes.get("manual", []):
        if not e.get("activo", True):
            continue
        clave = (e["source"], e["id"])
        if clave in vistos:
            continue
        vistos.add(clave)
        items.append({
            "id": e["id"], "title": e["title"], "year": e["year"],
            "approx": e.get("approx", False),
            "duration": e.get("duration", 0),
            "source": e["source"],
            "url": e.get("url", ""),
            "thumb": e.get("thumb", ""),
            "h": e.get("h", ""),
        })

    # --- canales y playlists de YouTube ---
    for url in fuentes.get("youtube", []):
        for linea in extraer_youtube(url):
            vid, titulo, dur = linea.split("|", 2)
            if ("youtube", vid) in vistos:
                continue
            vistos.add(("youtube", vid))
            anio, aprox = detectar_anio(titulo)
            if anio is None:
                sin_anio.append(f"{titulo}  [{vid}]")
                continue
            items.append({
                "id": vid, "title": titulo, "year": anio, "approx": aprox,
                "duration": int(dur) if dur.isdigit() else 0,
                "source": "youtube", "url": "",
            })

    if not items:
        sys.exit("✘ Ninguna fuente devolvió resultados; no se modifica nada.")

    items.sort(key=lambda x: (x["year"], x["title"]))
    catalogo = json.dumps(items, ensure_ascii=False)

    (AQUI / "catalog.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    html_path = AQUI / "index.html"
    html = html_path.read_text(encoding="utf-8")
    nuevo = re.sub(r"const CATALOGO = .*?;\n",
                   f"const CATALOGO = {catalogo};\n", html, count=1)
    html_path.write_text(nuevo, encoding="utf-8")

    print(f"✔ {len(items)} películas ({items[0]['year']}–{items[-1]['year']})")
    if sin_anio:
        print("⚠ Sin año detectado — añádelos en fuentes.json > manual con su año:")
        for t in sin_anio:
            print("  -", t)

if __name__ == "__main__":
    main()
