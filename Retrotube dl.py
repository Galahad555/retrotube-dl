#!/usr/bin/env python3
"""
mp3dl.py — Descargador de YouTube a MP3 y Video
Uso: python mp3dl.py
"""

import os
import sys
import re
import shutil
import subprocess

# ─── Colores ────────────────────────────────────────────────────────────────

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[36m"
YELLOW  = "\033[33m"
GREEN   = "\033[32m"
RED     = "\033[31m"

def c(color, text):  return f"{color}{text}{RESET}"
def titulo(texto):
    print()
    print(c(CYAN, "─" * 52))
    print(c(BOLD + CYAN, f"  {texto}"))
    print(c(CYAN, "─" * 52))
def separador():     print(c(DIM, "  " + "·" * 48))
def ok(msg):         print(c(GREEN,  f"  ✓ {msg}"))
def warn(msg):       print(c(YELLOW, f"  ⚠ {msg}"))
def err(msg):        print(c(RED,    f"  ✗ {msg}"))
def info(msg):       print(c(DIM,    f"  {msg}"))

# ─── Configuración ───────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    # Audio
    "calidad_audio":     "320",
    "carpeta_canciones": os.path.join(SCRIPT_DIR, "Canciones individuales"),
    "carpeta_playlists": os.path.join(SCRIPT_DIR, "Playlists"),
    "metadatos":         True,
    "historial":         True,
    # Video
    "formato_video":     "3gp",         # "3gp" | "avi_mpeg4" | "avi_h264"
    "carpeta_videos":    os.path.join(SCRIPT_DIR, "Videos"),
    # Modo activo
    "modo":              "audio",       # "audio" o "video"
}

CALIDADES_AUDIO = ["128", "192", "320"]

# Resolución nativa de la pantalla del BLU Diva Flex
VIDEO_W, VIDEO_H = 320, 240

FORMATOS_VIDEO = {
    "3gp": {
        "label":      "3GP + H.263  (confirmado funciona)",
        "extension":  "3gp",
        "vcodec":     "h263",
        "acodec":     "aac",
        # 352x288 es la otra resolución estándar de H.263 — más grande que
        # la pantalla, pero el celu la escala hacia abajo (mejor que hacia arriba)
        # qscale 5 (antes era 10) — mejora bastante la calidad visual
        "res_w":      352,
        "res_h":      288,
        "extra_v":    ["-qscale:v", "5"],
        "extra_a":    ["-b:a", "48k", "-ar", "22050", "-ac", "1"],
    },
    "avi_mpeg4": {
        "label":      "AVI + MPEG-4 Part 2  (probar — sin restricciones de H.263)",
        "extension":  "avi",
        "vcodec":     "mpeg4",
        "acodec":     "mp3",            # MP3 en AVI = más compatible que AAC
        # 320x240 exacto — pantalla del celu, sin escalar
        "res_w":      VIDEO_W,
        "res_h":      VIDEO_H,
        "extra_v":    ["-qscale:v", "5"],
        "extra_a":    ["-b:a", "64k", "-ar", "22050"],
    },
    "avi_h264": {
        "label":      "AVI + H.264  (algunos chips MediaTek lo leen en AVI pero no en MP4)",
        "extension":  "avi",
        "vcodec":     "libx264",
        "acodec":     "mp3",
        "res_w":      VIDEO_W,
        "res_h":      VIDEO_H,
        # -crf 28 = calidad media-baja, pesa poco; -preset ultrafast para velocidad
        "extra_v":    ["-crf", "28", "-preset", "ultrafast", "-profile:v", "baseline", "-level", "3.0"],
        "extra_a":    ["-b:a", "64k", "-ar", "22050"],
    },
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def sanitizar(nombre):
    nombre = re.sub(r'[\\/*?:"<>|]', "", nombre)
    return nombre.strip(". ") or "Sin nombre"

def input_prompt(msg, default=None):
    sufijo = f" [{c(DIM, default)}]" if default else ""
    r = input(f"  {BOLD}{msg}{RESET}{sufijo}: ").strip()
    return r if r else default

def confirmar(msg, default="s"):
    opciones = "S/n" if default == "s" else "s/N"
    r = input(f"  {BOLD}{msg}{RESET} ({opciones}): ").strip().lower()
    if not r:
        return default == "s"
    return r in ("s", "si", "sí", "y", "yes")

def verificar_ytdlp():
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        err("yt-dlp no está instalado.")
        info("Instalalo con:  pip install yt-dlp")
        sys.exit(1)

def verificar_ffmpeg():
    if not shutil.which("ffmpeg"):
        warn("ffmpeg no encontrado.")
        info("Instalalo con:  winget install ffmpeg  /  apt install ffmpeg  /  brew install ffmpeg")
        return False
    return True

# ─── Info sin descargar ──────────────────────────────────────────────────────

def obtener_info(url, ydl_mod):
    opts = {
        "quiet": True, "no_warnings": True,
        "extract_flat": "in_playlist", "skip_download": True,
    }
    with ydl_mod.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def es_playlist(datos):
    return datos.get("_type") == "playlist" or "entries" in datos

# ─── Preview / confirmación ──────────────────────────────────────────────────

def preview_single_audio(datos):
    titulo_raw   = datos.get("title", "Desconocido")
    uploader_raw = datos.get("uploader") or datos.get("channel") or "Desconocido"
    duracion     = datos.get("duration_string") or str(datos.get("duration", "?")) + "s"

    titulo("Vista previa — Audio individual")
    print(f"  {c(BOLD,'Título:  ')}{titulo_raw}")
    print(f"  {c(BOLD,'Canal:   ')}{uploader_raw}")
    print(f"  {c(BOLD,'Duración:')}{duracion}")
    separador()
    print(f"  {c(YELLOW,'Metadatos que se escribirán en el MP3:')}")
    print()

    song_title = input_prompt("Title  (nombre de la canción)", default=titulo_raw)
    artist     = input_prompt("Artist (artista)",              default=uploader_raw)
    album      = input_prompt("Album  (álbum)",                default="Canciones individuales")

    separador()
    print(f"  {c(BOLD,'Title: ')} {song_title}")
    print(f"  {c(BOLD,'Artist:')} {artist}")
    print(f"  {c(BOLD,'Album: ')} {album}")
    print()

    if not confirmar("¿Continuar con estos metadatos?"):
        return None
    return {"title": song_title, "artist": artist, "album": album}

def preview_playlist_audio(datos):
    nombre_pl = datos.get("title", "Playlist sin nombre")
    uploader  = datos.get("uploader") or datos.get("channel") or datos.get("id", "Desconocido")
    entries   = datos.get("entries", [])
    n_tracks  = len([e for e in entries if e])

    titulo("Vista previa — Playlist de audio")
    print(f"  {c(BOLD,'Playlist: ')}{nombre_pl}")
    print(f"  {c(BOLD,'Canal:    ')}{uploader}")
    print(f"  {c(BOLD,'Canciones:')}{n_tracks}{'  (+privadas/eliminadas)' if n_tracks != len(entries) else ''}")
    separador()
    print(f"  {c(YELLOW,'Metadatos para TODAS las canciones:')}")
    info("  (Title = nombre de cada video; Artist y Album iguales para todos)")
    print()

    artist = input_prompt("Artist", default=uploader)
    album  = input_prompt("Album",  default=nombre_pl)

    separador()
    print(f"  {c(BOLD,'Artist: ')} {artist}")
    print(f"  {c(BOLD,'Album:  ')} {album}")
    print(f"  {c(BOLD,'Carpeta:')} {os.path.join(CONFIG['carpeta_playlists'], sanitizar(album))}")
    print()

    if not confirmar("¿Continuar?"):
        return None
    return {"artist": artist, "album": album, "nombre_carpeta": sanitizar(album)}

def _info_formato_video():
    fmt   = CONFIG["formato_video"]
    fdata = FORMATOS_VIDEO[fmt]
    res_str = f"{fdata['res_w']}x{fdata['res_h']}"
    if fmt == "3gp":
        res_str += "  (H.263 — se escala al bajar en el celu)"
    elif fmt in ("avi_mpeg4", "avi_h264"):
        res_str += "  (pantalla exacta del BLU Diva Flex)"
    return fdata, res_str

def preview_single_video(datos):
    titulo_raw = datos.get("title", "Desconocido")
    uploader   = datos.get("uploader") or datos.get("channel") or "Desconocido"
    duracion   = datos.get("duration_string") or str(datos.get("duration", "?")) + "s"
    fdata, res_str = _info_formato_video()

    titulo("Vista previa — Video individual")
    print(f"  {c(BOLD,'Título:    ')}{titulo_raw}")
    print(f"  {c(BOLD,'Canal:     ')}{uploader}")
    print(f"  {c(BOLD,'Duración:  ')}{duracion}")
    separador()
    print(f"  {c(YELLOW,'Configuración de video:')}")
    print(f"  {c(BOLD,'Formato:   ')}{c(CYAN, fdata['label'])}")
    print(f"  {c(BOLD,'Resolución:')}{c(CYAN, res_str)}")
    print(f"  {c(BOLD,'Carpeta:   ')}{CONFIG['carpeta_videos']}")
    separador()

    nombre = input_prompt("Nombre del archivo (sin extensión)", default=titulo_raw)
    print()

    if not confirmar("¿Descargar?"):
        return None
    return {"nombre": nombre}

def preview_playlist_video(datos):
    nombre_pl = datos.get("title", "Playlist sin nombre")
    uploader  = datos.get("uploader") or datos.get("channel") or datos.get("id", "Desconocido")
    entries   = datos.get("entries", [])
    n_videos  = len([e for e in entries if e])
    fdata, res_str = _info_formato_video()

    titulo("Vista previa — Playlist de video")
    print(f"  {c(BOLD,'Playlist:  ')}{nombre_pl}")
    print(f"  {c(BOLD,'Canal:     ')}{uploader}")
    print(f"  {c(BOLD,'Videos:    ')}{n_videos}{'  (+privados/eliminados)' if n_videos != len(entries) else ''}")
    separador()
    print(f"  {c(YELLOW,'Configuración de video:')}")
    print(f"  {c(BOLD,'Formato:   ')}{c(CYAN, fdata['label'])}")
    print(f"  {c(BOLD,'Resolución:')}{c(CYAN, res_str)}")
    carpeta = os.path.join(CONFIG["carpeta_videos"], sanitizar(nombre_pl))
    print(f"  {c(BOLD,'Carpeta:   ')}{carpeta}")
    print()

    if not confirmar("¿Descargar toda la playlist?"):
        return None
    return {"nombre_carpeta": sanitizar(nombre_pl)}

# ─── Descarga audio ──────────────────────────────────────────────────────────

def build_metadata_args(meta):
    args = []
    for key, flag in [("artist", "artist"), ("album", "album"), ("title", "title")]:
        if meta.get(key):
            args += ["-metadata", f"{flag}={meta[key]}"]
    return args

def opciones_audio_base(carpeta, plantilla_nombre):
    postprocs = [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
         "preferredquality": CONFIG["calidad_audio"]},
    ]
    if CONFIG["metadatos"]:
        postprocs.append({"key": "FFmpegMetadata", "add_metadata": True})

    opts = {
        "format":         "bestaudio/best",
        "outtmpl":        os.path.join(carpeta, plantilla_nombre),
        "postprocessors": postprocs,
        "ignoreerrors":   True,
        "quiet":          False,
        "no_warnings":    False,
    }
    if CONFIG["historial"]:
        opts["download_archive"] = os.path.join(carpeta, ".historial.txt")
    return opts

def descargar_audio_single(url, meta, ydl_mod):
    carpeta = CONFIG["carpeta_canciones"]
    os.makedirs(carpeta, exist_ok=True)

    # Nombre de archivo tipo "Título - Artista" para que se vea el artista
    # aunque el reproductor no lea metadatos ID3 (celus viejos).
    if meta.get("artist"):
        nombre_archivo = sanitizar(f"{meta['title']} - {meta['artist']}")
    else:
        nombre_archivo = sanitizar(meta["title"])

    opts = opciones_audio_base(carpeta, f"{nombre_archivo}.%(ext)s")
    if CONFIG["metadatos"]:
        opts["postprocessor_args"] = {"ffmpegmetadata": build_metadata_args(meta)}

    ok(f"Descargando en: {carpeta}")
    print()
    with ydl_mod.YoutubeDL(opts) as ydl:
        ydl.download([url])
    print()
    ok("¡Listo!")

def descargar_audio_playlist(url, meta, ydl_mod):
    carpeta = os.path.join(CONFIG["carpeta_playlists"], meta["nombre_carpeta"])
    os.makedirs(carpeta, exist_ok=True)

    # Mismo criterio que en individual: "%(title)s - Artista.mp3"
    # El artista es el mismo para toda la playlist, así que va fijo en la plantilla
    # y el título de cada video lo pone yt-dlp dinámicamente.
    artista_seguro = sanitizar(meta["artist"])
    plantilla = f"%(title)s - {artista_seguro}.%(ext)s"

    opts = opciones_audio_base(carpeta, plantilla)
    if CONFIG["metadatos"]:
        opts["postprocessor_args"] = {
            "ffmpegmetadata": build_metadata_args({k: v for k, v in meta.items() if k in ("artist", "album")})
        }

    ok(f"Descargando en: {carpeta}")
    print()
    with ydl_mod.YoutubeDL(opts) as ydl:
        ydl.download([url])
    print()
    ok(f"¡Listo! MP3s en: {carpeta}")

# ─── Descarga video ──────────────────────────────────────────────────────────

def detectar_info_video(input_path):
    """Usa ffprobe para obtener codec y resolución del video descargado."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,width,height",
             "-of", "csv=p=0", input_path],
            capture_output=True, text=True
        )
        partes = result.stdout.strip().split(",")
        if len(partes) >= 3:
            return partes[0].strip(), int(partes[1]), int(partes[2])
    except Exception:
        pass
    return None, 0, 0

def encodear_video(input_path, output_path, fdata, w, h):
    """Llama a ffmpeg para convertir el video descargado al formato del celu."""
    info(f"  Re-encodeando: {os.path.basename(output_path)}")

    fmt = CONFIG["formato_video"]

    if fmt == "avi_h264":
        # H.264 en AVI — baseline profile para máxima compatibilidad
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"scale={w}:{h},setsar=1",
            "-vcodec", "libx264",
            *fdata["extra_v"],
            "-acodec", "mp3",
            *fdata["extra_a"],
            "-f", "avi",
            output_path,
        ]

    elif fmt == "avi_mpeg4":
        # MPEG-4 Part 2 en AVI — compatible con reproductores básicos
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"scale={w}:{h},setsar=1",
            "-vcodec", "mpeg4",
            *fdata["extra_v"],
            "-acodec", "mp3",
            *fdata["extra_a"],
            "-f", "avi",
            output_path,
        ]

    else:
        # 3GP / H.263
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"scale={w}:{h},setsar=1",
            "-vcodec", fdata["vcodec"],
            *fdata["extra_v"],
            "-acodec", fdata["acodec"],
            *fdata["extra_a"],
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        err("ffmpeg falló al encodear el video.")
        return False

    if input_path != output_path and os.path.exists(input_path):
        os.remove(input_path)
    return True

def opciones_video_descarga(carpeta, plantilla):
    """Opciones de yt-dlp solo para BAJAR el video crudo, sin encodear todavía."""
    opts = {
        "format":        "worstvideo[ext=mp4]+worstaudio/worst/bestvideo[height<=480]+bestaudio",
        "outtmpl":       os.path.join(carpeta, plantilla),
        "ignoreerrors":  True,
        "quiet":         False,
        "no_warnings":   False,
        "merge_output_format": "mp4",
    }
    if CONFIG["historial"]:
        opts["download_archive"] = os.path.join(carpeta, ".historial_video.txt")
    return opts

def descargar_video_single(url, meta, ydl_mod):
    carpeta = CONFIG["carpeta_videos"]
    os.makedirs(carpeta, exist_ok=True)

    fmt   = CONFIG["formato_video"]
    fdata = FORMATOS_VIDEO[fmt]
    ext   = fdata["extension"]
    w, h  = fdata["res_w"], fdata["res_h"]

    nombre_seguro = sanitizar(meta["nombre"])

    # Paso 1: bajar el video crudo
    temp_plantilla = f"{nombre_seguro}_tmp.%(ext)s"
    opts = opciones_video_descarga(carpeta, temp_plantilla)

    ok(f"Descargando en: {carpeta}")
    info("  Paso 1/2: bajando video...")
    print()

    with ydl_mod.YoutubeDL(opts) as ydl:
        ydl.download([url])

    temp_archivo = _encontrar_temp(carpeta, f"{nombre_seguro}_tmp")
    if not temp_archivo:
        err("No se encontró el archivo descargado para encodear.")
        return

    # Paso 2: encodear al formato del celu
    print()
    info("  Paso 2/2: convirtiendo al formato del celu...")

    output_path = os.path.join(carpeta, f"{nombre_seguro}.{ext}")
    if encodear_video(temp_archivo, output_path, fdata, w, h):
        print()
        ok(f"¡Listo!  →  {output_path}")
    else:
        warn(f"El archivo temporal quedó en: {temp_archivo}")

def descargar_video_playlist(url, meta, ydl_mod):
    carpeta = os.path.join(CONFIG["carpeta_videos"], meta["nombre_carpeta"])
    os.makedirs(carpeta, exist_ok=True)

    fmt   = CONFIG["formato_video"]
    fdata = FORMATOS_VIDEO[fmt]
    ext   = fdata["extension"]
    w, h  = fdata["res_w"], fdata["res_h"]

    opts = opciones_video_descarga(carpeta, "%(title)s_tmp.%(ext)s")

    ok(f"Descargando en: {carpeta}")
    info("  Paso 1/2: bajando todos los videos...")
    print()

    with ydl_mod.YoutubeDL(opts) as ydl:
        ydl.download([url])

    print()
    info("  Paso 2/2: convirtiendo al formato del celu...")
    archivos_tmp = [
        f for f in os.listdir(carpeta)
        if "_tmp." in f and not f.startswith(".")
    ]

    if not archivos_tmp:
        warn("No se encontraron archivos para encodear.")
        return

    for archivo in sorted(archivos_tmp):
        input_path  = os.path.join(carpeta, archivo)
        nombre_base = archivo.rsplit("_tmp.", 1)[0]
        output_path = os.path.join(carpeta, f"{nombre_base}.{ext}")
        encodear_video(input_path, output_path, fdata, w, h)

    print()
    ok(f"¡Listo! Videos en: {carpeta}")

def _encontrar_temp(carpeta, prefijo):
    """Encuentra el archivo _tmp descargado (extensión desconocida de antemano)."""
    for f in os.listdir(carpeta):
        if f.startswith(prefijo) and not f.startswith("."):
            return os.path.join(carpeta, f)
    return None

# ─── Menú settings ───────────────────────────────────────────────────────────

def menu_settings():
    titulo("Configuración")

    # Modo
    modo_actual = c(CYAN, "🎵 Audio (MP3)") if CONFIG["modo"] == "audio" else c(CYAN, "🎬 Video")
    print(f"  {c(BOLD,'1.')} Modo de descarga:  {modo_actual}")
    if confirmar("¿Cambiar al otro modo?", default="n"):
        CONFIG["modo"] = "video" if CONFIG["modo"] == "audio" else "audio"
        nuevo = "🎬 Video" if CONFIG["modo"] == "video" else "🎵 Audio (MP3)"
        ok(f"Modo → {nuevo}")

    separador()

    if CONFIG["modo"] == "audio":
        print(f"  {c(BOLD,'2.')} Calidad de audio")
        print(f"     Actual: {c(CYAN, CONFIG['calidad_audio'])} kbps   |   Opciones: {' / '.join(CALIDADES_AUDIO)}")
        nueva = input_prompt("Nueva calidad (Enter para mantener)", default=CONFIG["calidad_audio"])
        if nueva in CALIDADES_AUDIO:
            CONFIG["calidad_audio"] = nueva
            ok(f"Calidad → {nueva} kbps")
        elif nueva != CONFIG["calidad_audio"]:
            warn(f"'{nueva}' no es válida")

        separador()
        print(f"  {c(BOLD,'3.')} Carpeta canciones individuales")
        print(f"     {c(DIM, CONFIG['carpeta_canciones'])}")
        nueva = input_prompt("Nueva carpeta (Enter para mantener)", default=CONFIG["carpeta_canciones"])
        if nueva and nueva != CONFIG["carpeta_canciones"]:
            CONFIG["carpeta_canciones"] = os.path.expanduser(nueva)
            ok(f"Carpeta → {CONFIG['carpeta_canciones']}")

        separador()
        print(f"  {c(BOLD,'4.')} Carpeta base para playlists")
        print(f"     {c(DIM, CONFIG['carpeta_playlists'])}")
        nueva = input_prompt("Nueva carpeta (Enter para mantener)", default=CONFIG["carpeta_playlists"])
        if nueva and nueva != CONFIG["carpeta_playlists"]:
            CONFIG["carpeta_playlists"] = os.path.expanduser(nueva)
            ok(f"Carpeta → {CONFIG['carpeta_playlists']}")

        separador()
        estado = c(GREEN, "activados") if CONFIG["metadatos"] else c(RED, "desactivados")
        print(f"  {c(BOLD,'5.')} Metadatos ID3: {estado}")
        if confirmar("¿Cambiar?", default="n"):
            CONFIG["metadatos"] = not CONFIG["metadatos"]
            ok(f"Metadatos → {'activados' if CONFIG['metadatos'] else 'desactivados'}")

    else:
        fmt_actual = FORMATOS_VIDEO[CONFIG["formato_video"]]["label"]
        print(f"  {c(BOLD,'2.')} Formato de video")
        print(f"     Actual: {c(CYAN, fmt_actual)}")
        print()
        keys = list(FORMATOS_VIDEO.keys())
        for i, key in enumerate(keys, 1):
            marca = c(GREEN, "✓ ") if key == CONFIG["formato_video"] else "  "
            print(f"     {marca}{i}. {FORMATOS_VIDEO[key]['label']}")
        print()
        eleccion = input_prompt(f"Elegí 1, 2 o 3 (Enter para mantener)", default="")
        if eleccion in ("1", "2", "3"):
            idx = int(eleccion) - 1
            if idx < len(keys):
                CONFIG["formato_video"] = keys[idx]
                ok(f"Formato → {FORMATOS_VIDEO[keys[idx]]['label']}")

        separador()
        print(f"  {c(BOLD,'3.')} Carpeta para videos")
        print(f"     {c(DIM, CONFIG['carpeta_videos'])}")
        nueva = input_prompt("Nueva carpeta (Enter para mantener)", default=CONFIG["carpeta_videos"])
        if nueva and nueva != CONFIG["carpeta_videos"]:
            CONFIG["carpeta_videos"] = os.path.expanduser(nueva)
            ok(f"Carpeta → {CONFIG['carpeta_videos']}")

    separador()
    estado = c(GREEN, "activado") if CONFIG["historial"] else c(RED, "desactivado")
    print(f"  {c(BOLD,'·')} Historial: {estado}")
    if confirmar("¿Cambiar?", default="n"):
        CONFIG["historial"] = not CONFIG["historial"]
        ok(f"Historial → {'activado' if CONFIG['historial'] else 'desactivado'}")

    print()

# ─── Pantalla principal ──────────────────────────────────────────────────────

def mostrar_estado():
    modo = CONFIG["modo"]
    titulo("✦ mp3dl — Descargador de YouTube")

    if modo == "audio":
        meta_str = c(GREEN, "on") if CONFIG["metadatos"] else c(RED, "off")
        hist_str = c(GREEN, "on") if CONFIG["historial"]  else c(RED, "off")
        print(f"  Modo: {c(CYAN,'🎵 Audio MP3')}  {c(CYAN, CONFIG['calidad_audio'])} kbps  |  Metadatos: {meta_str}  |  Historial: {hist_str}")
        print(f"  Individuales: {c(DIM, CONFIG['carpeta_canciones'])}")
        print(f"  Playlists:    {c(DIM, CONFIG['carpeta_playlists'])}")
    else:
        fmt   = CONFIG["formato_video"]
        fdata = FORMATOS_VIDEO[fmt]
        hist_str = c(GREEN, "on") if CONFIG["historial"] else c(RED, "off")
        res = f"{fdata['res_w']}x{fdata['res_h']}"
        print(f"  Modo: {c(CYAN,'🎬 Video')}  {c(CYAN, fdata['extension'].upper())}  {c(CYAN, fdata['vcodec'])}  {c(CYAN, res)}  |  Historial: {hist_str}")
        print(f"  Videos: {c(DIM, CONFIG['carpeta_videos'])}")

    separador()
    print(f"  Pegá un {c(BOLD,'link de YouTube')} para descargar.")
    print(f"  Escribí  {c(BOLD,'settings')} (o {c(BOLD,'s')})  para cambiar la config.")
    print(f"  Escribí  {c(BOLD,'salir')}    (o {c(BOLD,'q')})  para salir.")
    print()

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ydl_mod = verificar_ytdlp()
    verificar_ffmpeg()

    while True:
        mostrar_estado()

        try:
            entrada = input(f"  {c(BOLD + CYAN, '→')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            info("Hasta luego ✦")
            break

        if not entrada:
            continue

        if entrada.lower() in ("salir", "exit", "q", "quit"):
            info("Hasta luego ✦")
            break

        if entrada.lower() in ("settings", "setting", "s", "config", "configuracion", "configuración"):
            menu_settings()
            continue

        if not (entrada.startswith("http://") or entrada.startswith("https://")):
            err("Eso no parece una URL válida. Probá con https://...")
            continue

        print()
        info("Obteniendo información del link...")

        try:
            datos = obtener_info(entrada, ydl_mod)
        except Exception as e:
            err(f"No se pudo obtener información: {e}")
            continue

        if not datos:
            err("No se encontró nada en ese link.")
            continue

        try:
            modo  = CONFIG["modo"]
            es_pl = es_playlist(datos)

            if modo == "audio":
                if es_pl:
                    meta = preview_playlist_audio(datos)
                    if meta is None: continue
                    descargar_audio_playlist(entrada, meta, ydl_mod)
                else:
                    meta = preview_single_audio(datos)
                    if meta is None: continue
                    descargar_audio_single(entrada, meta, ydl_mod)
            else:
                if es_pl:
                    meta = preview_playlist_video(datos)
                    if meta is None: continue
                    descargar_video_playlist(entrada, meta, ydl_mod)
                else:
                    meta = preview_single_video(datos)
                    if meta is None: continue
                    descargar_video_single(entrada, meta, ydl_mod)

        except KeyboardInterrupt:
            print()
            warn("Descarga interrumpida.")
        except Exception as e:
            err(f"Error durante la descarga: {e}")

        print()


if __name__ == "__main__":
    main()
