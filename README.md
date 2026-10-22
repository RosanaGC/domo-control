# Domo — visuales para planetario

Visuales reactivos al audio en formato **domemaster** (fisheye 180° / 210°) para proyectar en un domo
mientras toca una banda. Corre en el navegador (Chrome) desde tu propio Mac, sin internet.

`Domo Control.html` es la aplicación principal: partículas, gaussian splats (`.ply` / `.splat`) y video
como capas mezclables, con secuencia de escenas, control en vivo y render cuadro por cuadro a video.

## Correrlo (Mac)

Necesitas **Google Chrome** y **python3** (viene con las herramientas de línea de comandos de macOS).

1. Clona o descarga el repositorio:
   ```
   git clone https://github.com/RosanaGC/domo-control.git
   ```
2. Solo la primera vez, en Terminal dentro de la carpeta:
   ```
   chmod +x iniciar.command
   ```
3. Doble clic en `iniciar.command`. Se abre http://localhost:8080 → **Domo Control**.
   - Si macOS lo bloquea: clic derecho → Abrir.

O a mano:
```
cd domo-control
python3 servidor.py
```
y abre http://localhost:8080/Domo%20Control.html en Chrome.

Hay que abrirlo desde `localhost` (no con doble clic al `.html`): si no, el micrófono y la carga
de escenas no funcionan, ni se guardan los proyectos. Para detener: cierra la Terminal o `Ctrl + C`.

## Proyectos

Al abrir la app te pide un **nombre de proyecto** (o abrir uno que ya existe). Todo lo del proyecto se
guarda solo en una carpeta dentro de domo-control:

```
proyectos/<nombre>/
  proyecto.json   ajustes, orden y segundos de las escenas, formato de render
  escenas/        copias de los .ply / .splat
  musica/         la canción (sirve para el render y para tocarla en vivo)
  video/          el video de la capa de video
```

Al recargar (`Cmd + R`) o al volver otro día se abre el último proyecto con todo cargado. Arriba del
panel, **Nuevo / abrir** crea otro proyecto (empieza vacío, con los ajustes actuales) o abre uno de la
lista, y **Guardar** guarda en el momento (igual se guarda solo a cada cambio). Mientras copia archivos
grandes dice *Guardando…*: no recargues hasta que diga *Guardado*. Quitar una escena de la lista borra su
copia del proyecto (el archivo original no se toca). La música se elige en **Renderizar canción** o en
AUDIO → Archivo; con un proyecto abierto aparece el botón **▶ Tocar música del proyecto**.

Para respaldar o pasar un proyecto a otro Mac, copia su carpeta dentro de `proyectos/`. La carpeta
`proyectos/` no se sube a git (es pesada y personal). Lo guarda `servidor.py`, que arranca
`iniciar.command`: solo acepta conexiones de este mismo equipo.

## Uso

**Guía**: la primera vez se abre sola una guía paso a paso para armar y renderizar un proyecto
(proyecto → formato domo → contenido → canción → formato de salida → render → verificar). Cada paso se marca
solo cuando está listo. Con `—` (o `Esc` / `H`) se minimiza a una barrita arriba a la izquierda con el
paso actual; clic en ella (o `H`) la vuelve a abrir. Con ✕ en la barrita se oculta del todo y vuelve con
`H` o el botón **Guía** arriba del panel. No aparece en pantalla completa.

**Capas** (de abajo hacia arriba): video, gaussian splats, partículas. Cada una con interruptor,
opacidad y modo de mezcla. Todos los parámetros se ajustan en vivo y se guardan solos en el proyecto
(también se pueden exportar / importar como `.json`).

**Splats**: agrega tus `.ply` / `.splat` (de Postshot, Polycam, Luma, KIRI…) con el botón o
arrastrándolos a la página. A cada escena le pones los segundos que dura y le das a **▶ Secuencia**:
pasan de una a otra con fundido, precargando la siguiente para que el cambio no se note.
La lista, el orden y los tiempos quedan en el proyecto.

**Ajustes por escena**: cada escena guarda sus propios ajustes de splats (recorrido, velocidad, alcance,
inclinación, fundido, etc.). Haz clic en una escena de la lista para mostrarla y ajusta los controles:
cambian solo esa escena (en la lista se ve el recorrido de cada una). Cuando la secuencia o el render pasan
a otra escena se aplican los suyos, y durante el fundido cada una se mueve a su manera. **Variar al azar**
le da a la escena elegida un movimiento distinto (recorrido, velocidad, inclinación, alcance…) para que el
video no sea monótono; **Copiar a todas** pasa los ajustes de esa escena a las demás. Las escenas nuevas
arrancan con los ajustes de la que está en pantalla.

**Recorrido de la cámara** (en la capa de splats): *Órbita* gira alrededor de la escena; *Viajar por dentro*
recorre todo el volumen de la escena por adentro, mirando hacia donde va (pasa entre los objetos y a veces
los atraviesa); **Alcance** es hasta dónde llega: 1 ≈ el borde de la escena, más de 1 sale afuera y vuelve a
entrar. **Transparencia cerca** hace transparentes los splats que pasan pegados a la cámara para que no
tapen todo. **Variación altura** (en *Viajar por dentro* y *Libre*) es cuánto sube y baja la cámara mientras
recorre: 0 casi a la misma altura, 1 recorre de abajo arriba. *Entrar y salir*
se mete y sale con vaivén regular; *Libre (va variando)* se mete y sale a ritmo irregular y va cambiando
el radio, la altura y la inclinación de la órbita, sin repetirse. **Variación** es cuánto cambia (0 = órbita
fija) y **Ritmo cambios** cada cuántos segundos aprox. da una vuelta de cambios. Con **Sentido** en *Alternar*,
en modo Libre el giro también se invierte de vez en cuando, suave.
En *Entrar y salir* también cambia, de una pasada a otra, cuánto se mete y a qué altura va.
**Mover con música** (en todos los recorridos) hace que la cámara siga lento la intensidad de la canción:
en las partes fuertes se mete un poco y sube, en las tranquilas sale y baja. Compara los últimos ~4 s con
el promedio de la canción, así que no reacciona a cada golpe sino a cómo va cambiando. 0 lo apaga.

**Audio en vivo**: conecta una salida de la consola a una interfaz de audio, elígela en el selector
bajo los botones de audio y aprieta **Mic**. Ajusta **Ganancia** y **Umbral golpe** mirando el medidor.
**Reacción** y **Suavidad** controlan cuánto y qué tan suave responde todo a cada golpe.
**Fluidez** decide cómo se mueve con los golpes: en 0 cada golpe da un tirón corto (acelera y frena);
en 1 los golpes se suman a un impulso que sube y baja lento, y el movimiento sigue sin saltos. Por defecto 0,8.

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
| `H` | guía de proyecto: abrir / minimizar |

## Render a video

Para entregar al planetario, **Renderizar canción** genera el video cuadro por cuadro usando una
canción como guía de la reacción: sale perfectamente fluido aunque el equipo no alcance tiempo real
(tarda lo que tenga que tardar). Usa las capas, ajustes, formato domo y secuencia de escenas actuales.
Sale sin audio (en el show suena la banda en vivo). Solo en Chrome.

Por defecto sale en el formato del planetario: **domemaster 210°, 4096×4096, 30 fps, MP4 H.265**
(`domo-4096-cancion.mp4`, listo para entregar). Lo codifica el chip del Mac desde Chrome; si el equipo
no puede hacer H.265 a esa resolución, la app lo avisa y hay que usar la secuencia PNG.
La resolución del render es independiente de la de la vista en vivo; 2048 sirve para el video de postulación.

**Secuencia PNG** (sin pérdida): eliges una carpeta y dentro se crea `domo-4096-cancion/` con
`cuadro_000000.png`, `cuadro_000001.png`… Ojo con el espacio en disco: cada cuadro 4096 pesa varios MB.
Para la máxima calidad, el MP4 H.265 se arma desde la secuencia con ffmpeg (una sola compresión):
```
brew install ffmpeg
cd domo-4096-cancion
ffmpeg -framerate 30 -i cuadro_%06d.png -c:v libx265 -preset slow -crf 16 -pix_fmt yuv420p -tag:v hvc1 domo-4096-cancion.mp4
```
Para la postulación (2048, H.264):
```
ffmpeg -framerate 30 -i cuadro_%06d.png -c:v libx264 -crf 16 -pix_fmt yuv420p domo-2048-cancion.mp4
```

El formato **Video WebM** (VP9) queda como prueba rápida: pesa mucho menos y permite incluir el audio
para revisar, pero comprime con pérdida.

## Archivos

- `Domo Control.html` — la aplicación.
- `lib/mp4-muxer.js` — [mp4-muxer](https://github.com/Vanilagy/mp4-muxer) 5.2.2 (MIT), arma el MP4 H.265 del render.
- `lib/webm-muxer.js` — [webm-muxer](https://github.com/Vanilagy/webm-muxer) 5.1.4 (MIT), arma el WebM del render.
- `Domo Visuales.dc.html`, `Domo Splats.dc.html`, `Domo Video.dc.html`, `support.js` — versiones originales separadas (necesitan internet).
- `index.html` — menú de inicio. `iniciar.command` — arranca el servidor local.
- `servidor.py` — servidor local: sirve la app y guarda los proyectos en `proyectos/`.
