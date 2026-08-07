# mp3dl 🎵

Descargador de YouTube por consola, pensado para bajar canciones sueltas o playlists enteras como **MP3**, o videos convertidos a un formato compatible con celulares viejos (como el BLU Diva Flex).

## Características

- 🎵 **Modo audio**: descarga en MP3 (128/192/320 kbps) con metadatos ID3 (Title, Artist, Album)
- 🎬 **Modo video**: descarga y reencodea a 3GP (H.263), AVI+MPEG-4 o AVI+H.264, con resolución ajustada a pantallas chicas
- 📁 Soporta tanto videos/canciones individuales como playlists completas
- 📝 Los archivos de audio se guardan como `Título - Artista.mp3`, para que se vea el artista aunque el reproductor no lea metadatos
- 🗂️ Historial de descargas para no repetir lo ya bajado
- ⚙️ Menú de configuración interactivo (calidad, carpetas, formato de video, etc.)

## Requisitos

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) instalado y disponible en el PATH
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

### Instalación de ffmpeg

```bash
# Windows
winget install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Instalación de yt-dlp

```bash
pip install yt-dlp
```

## Uso

```bash
python mp3dl.py
```

Al iniciar vas a ver un menú simple:

- Pegá un **link de YouTube** (video o playlist) y presioná Enter para descargarlo
- Escribí `settings` (o `s`) para cambiar la configuración
- Escribí `salir` (o `q`) para salir

### Modo audio

Al pegar un link, el script te va a mostrar una vista previa con el título, canal y duración, y te va a pedir confirmar (o editar) los metadatos `Title`, `Artist` y `Album` antes de descargar.

### Modo video

Podés elegir entre tres formatos de salida según el celular donde vayas a reproducir el video:

| Formato | Extensión | Codec de video | Notas |
|---|---|---|---|
| 3GP | `.3gp` | H.263 | El más compatible con celulares antiguos |
| AVI + MPEG-4 | `.avi` | MPEG-4 Part 2 | Sin las restricciones de resolución de H.263 |
| AVI + H.264 | `.avi` | H.264 (baseline) | Algunos chips MediaTek lo leen en AVI pero no en MP4 |

## Estructura de carpetas

Por defecto, dentro de la carpeta del script se crean:

```
mp3dl/
├── Canciones individuales/
├── Playlists/
│   └── <nombre del álbum>/
└── Videos/
    └── <nombre de la playlist>/
```

Todas estas rutas se pueden cambiar desde el menú de `settings`.

## Configuración

Desde `settings` podés ajustar:

- Modo de descarga (audio / video)
- Calidad de audio (128 / 192 / 320 kbps)
- Formato de video (3GP / AVI+MPEG-4 / AVI+H.264)
- Carpetas de destino
- Activar o desactivar metadatos ID3
- Activar o desactivar el historial de descargas

## Aviso

Este script es para uso personal. Respetá los derechos de autor del contenido que descargues y los términos de servicio de YouTube.
