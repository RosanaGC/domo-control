# Domo — visuales para planetario

Visuales reactivos al audio en formato **domemaster** (fisheye 180° / 210°) para proyectar en un domo
mientras toca una banda. Corre en el navegador (Chrome) desde tu propio Mac, sin internet.

`Domo Control.html` es la aplicación principal: partículas, gaussian splats (`.ply` / `.splat`) y video
como capas mezclables, con secuencia de escenas, control en vivo y render cuadro por cuadro a video.

## Correrlo (Mac)

Necesitas **Google Chrome** y **python3** (viene con las herramientas de línea de comandos de macOS).

1. Clona o descarga el repositorio.
2. Solo la primera vez, en Terminal dentro de la carpeta:
   ```
   chmod +x iniciar.command
   ```
3. Doble clic en `iniciar.command`. Se abre http://localhost:8080 → **Domo Control**.
   - Si macOS lo bloquea: clic derecho → Abrir.

O a mano:
```
cd domo
python3 -m http.server 8080
```
y abre http://localhost:8080/Domo%20Control.html en Chrome.

Hay que abrirlo desde `localhost` (no con doble clic al `.html`): si no, el micrófono y la carga
de escenas no funcionan. Para detener: cierra la Terminal o `Ctrl + C`.

## Uso

**Capas** (de abajo hacia arriba): video, gaussian splats, partículas. Cada una con interruptor,
opacidad y modo de mezcla. Todos los parámetros se ajustan en vivo y se guardan solos en el navegador
(también se pueden exportar / importar como `.json`).

**Splats**: agrega tus `.ply` / `.splat` (de Postshot, Polycam, Luma, KIRI…) con el botón o
arrastrándolos a la página. A cada escena le pones los segundos que dura y le das a **▶ Secuencia**:
pasan de una a otra con fundido, precargando la siguiente para que el cambio no se note. La lista no
se guarda al recargar la página (los tiempos sí, por nombre de archivo). Los archivos de escenas no
van en este repositorio por su tamaño.

**Audio en vivo**: conecta una salida de la consola a una interfaz de audio, elígela en el selector
bajo los botones de audio y aprieta **Mic**. Ajusta **Ganancia** y **Umbral golpe** mirando el medidor.
**Reacción** y **Suavidad** controlan cuánto y qué tan suave responde todo a cada golpe.

**Formato domo**: 210° (recomendado) o 180°. En 210° la guía en pantalla marca el horizonte.

**Atajos**

| Tecla | Acción |
|---|---|
| `Espacio` | golpe manual |
| `T` | tap tempo |
| `1` `2` `3` | activar / apagar partículas, splats, video |
| `N` / `B` | escena siguiente / anterior |
| `P` | secuencia play / pausa |
| `D` | invertir sentido de giro |
| `R` | grabar en vivo |
| `F` | pantalla completa |
| `G` | mostrar / ocultar guía |

## Render a video

Para entregar al planetario, **Renderizar canción** genera el video cuadro por cuadro usando una
canción como guía de la reacción: sale perfectamente fluido aunque el equipo no alcance tiempo real
(tarda lo que tenga que tardar). Usa las capas, ajustes, resolución y secuencia de escenas actuales.
Por defecto sale sin audio (en el show suena la banda en vivo). Solo en Chrome.

El render sale en `.webm` (VP9). Para pasarlo a MP4 H.265 4096×4096 30 fps:
```
brew install ffmpeg
```
Rápido (usa el chip del Mac):
```
ffmpeg -i domo-4096-cancion.webm -c:v hevc_videotoolbox -q:v 75 -pix_fmt yuv420p -tag:v hvc1 -an domo-4096-cancion.mp4
```
Máxima calidad (mucho más lento):
```
ffmpeg -i domo-4096-cancion.webm -c:v libx265 -preset slow -crf 16 -pix_fmt yuv420p -tag:v hvc1 -an domo-4096-cancion.mp4
```

## Archivos

- `Domo Control.html` — la aplicación.
- `lib/webm-muxer.js` — [webm-muxer](https://github.com/Vanilagy/webm-muxer) 5.1.4 (MIT), arma el archivo de video del render.
- `Domo Visuales.dc.html`, `Domo Splats.dc.html`, `Domo Video.dc.html`, `support.js` — versiones originales separadas (necesitan internet).
- `index.html` — menú de inicio. `iniciar.command` — arranca el servidor local.
