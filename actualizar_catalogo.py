#!/usr/bin/env python3
"""
Actualiza el catálogo cronológico del Archivo Fílmico de Palestina.

Uso:
    pip install yt-dlp
    python3 actualizar_catalogo.py

Extrae todos los videos del canal con yt-dlp (sin API key), detecta el año
de filmación en el título y reescribe el catálogo embebido en index.html.
"""
import json, re, subprocess, sys
from pathlib import Path

CANAL = "https://www.youtube.com/@ArchivoFilmicodePalestina/videos"
AQUI = Path(__file__).parent

def extraer_videos():
    r = subprocess.run(
        ["yt-dlp", "--flat-playlist",
         "--print", "%(id)s|%(title)s|%(duration)s", CANAL],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"yt-dlp falló:\n{r.stderr[-500:]}")
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
    m = re.search(r"años (\d{2})", titulo)  # "años 50"
    if m:
        return 1900 + int(m.group(1)), True
    return None, True

def main():
    items, sin_anio = [], []
    for linea in extraer_videos():
        vid, titulo, dur = linea.split("|", 2)
        anio, aprox = detectar_anio(titulo)
        if anio is None:
            sin_anio.append(titulo)
            continue
        items.append({"id": vid, "title": titulo, "year": anio,
                      "approx": aprox,
                      "duration": int(dur) if dur.isdigit() else 0})

    items.sort(key=lambda x: (x["year"], x["title"]))
    catalogo = json.dumps(items, ensure_ascii=False)

    # guarda copia independiente
    (AQUI / "catalog.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    # reinyecta en index.html
    html_path = AQUI / "index.html"
    html = html_path.read_text(encoding="utf-8")
    nuevo = re.sub(r"const CATALOGO = .*?;\n",
                   f"const CATALOGO = {catalogo};\n", html, count=1)
    html_path.write_text(nuevo, encoding="utf-8")

    print(f"✔ {len(items)} películas ({items[0]['year']}–{items[-1]['year']})")
    if sin_anio:
        print("⚠ Sin año detectado (revisar título):")
        for t in sin_anio:
            print("  -", t)

if __name__ == "__main__":
    main()
