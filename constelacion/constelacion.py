#!/usr/bin/env python3
"""Una constelación que se forma sobre la lluvia de estrellas (secuencia JPG domemaster).

Cada estrella nace cerca del centro, viaja hacia afuera con la lluvia, frena y queda fija con un destello.
Después se trazan las líneas y aparece la sombra: la silueta de la figura en azul claro (de descomponer.py)
o, si no hay silueta, una sombra difusa armada con los trazos de la figura. Los cuadros van directo a ffmpeg: una sola compresión,
sin PNG intermedios.

  python3 constelacion.py orion.json --prueba              # 2048, rápido, para ver en QuickTime
  python3 constelacion.py orion.json --prueba --desde 55   # solo desde el segundo 55
  python3 constelacion.py orion.json                       # 4096 H.265 final para el planetario
  python3 constelacion.py orion.json --audio cancion.wav   # con música
"""
import argparse, base64, io, json, math, os, subprocess, sys, time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

COLOR_ESTRELLA = np.array([0.88, 0.95, 1.0], np.float32)
COLOR_LINEA = np.array([0.65, 0.82, 1.0], np.float32)
COLOR_FIGURA = np.array([1.0, 0.8, 0.52], np.float32)
COLOR_SOMBRA = np.array([0.55, 0.77, 1.0], np.float32)


def clamp01(t): return min(1.0, max(0.0, t))
def suave(t): t = clamp01(t); return t * t * (3 - 2 * t)
def mas_suave(t): t = clamp01(t); return t * t * t * (t * (6 * t - 15) + 10)


def catmull_rom(pts, n=16):
    if len(pts) < 3: return pts
    p = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = (np.array(q, float) for q in p[i - 1:i + 3])
        for s in range(n):
            t = s / n
            out.append(tuple(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3)))
    return out + [tuple(pts[-1])]


class Constelacion:
    def __init__(self, cfg, W):
        self.cfg, self.W, self.k = cfg, W, W / 4096
        cx, cy = cfg['centro']
        self.px = lambda x, y: (cx * W + x * cfg['escala'] * W, cy * W - y * cfg['escala'] * W)
        self.origen = np.array([W / 2, W / 2])  # la lluvia sale del centro del domo

        n = len(cfg['estrellas'])
        t0, t1 = cfg['estrellas_inicio'], cfg['estrellas_fin']
        self.estrellas = {}
        for i, (nombre, x, y, mag) in enumerate(cfg['estrellas']):
            amp = min(1.0, max(0.4, 10 ** (-0.2 * (mag - 0.5))))
            fija = t0 + i * (t1 - t0) / max(1, n - 1)
            self.estrellas[nombre] = dict(pos=np.array(self.px(x, y)), amp=amp, fija=fija, fase=i * 2.39)

        # Recorte donde pasa todo: estrellas, figura y el camino desde el centro, con margen para el brillo
        pts = [s['pos'] for s in self.estrellas.values()] + [self.origen]
        for tr in cfg['figura_trazos']:
            pts += [np.array(self.px(tr[0] + dx, tr[1] + dy)) for dx in (-tr[2], tr[2]) for dy in (-tr[2], tr[2])] \
                if not isinstance(tr[0], list) else [np.array(self.px(*q)) for q in tr]
        if cfg.get('silueta'):
            pts += [np.array(self.px(x, y)) for x in cfg['silueta']['x'] for y in cfg['silueta']['y']]
        pts = np.array(pts)
        self.difuso = cfg.get('sombra_difuso', 0.9) * cfg['escala'] * W  # desenfoque de la sombra
        m = int(max(80 * self.k, 3 * self.difuso))
        self.x0, self.y0 = (max(0, int(v) - m) for v in pts.min(0))
        self.x1, self.y1 = (min(W, int(v) + m) for v in pts.max(0))
        self.capa_figura = self._dibujar_figura()
        self.capa_sombra = self._dibujar_sombra() if cfg.get('sombra') else None
        self.capa_lineas_final = None

    def _local(self, p): return (p[0] - self.x0, p[1] - self.y0)

    def _forma(self): return (self.y1 - self.y0, self.x1 - self.x0)

    def _brillo(self, img, ancho, nitidez, glow):
        """Trazo fino + resplandor difuso, en 0..1."""
        a = np.asarray(img, np.float32) / 255
        g = np.asarray(img.filter(ImageFilter.GaussianBlur(ancho)), np.float32) / 255
        return nitidez * a + glow * g

    def _dibujar_figura(self):
        img = Image.new('L', self._forma()[::-1], 0)
        d = ImageDraw.Draw(img)
        w = max(1, round(3 * self.k))
        for tr in self.cfg['figura_trazos']:
            if not isinstance(tr[0], list):
                (cx, cy), r = self._local(self.px(tr[0], tr[1])), tr[2] * self.cfg['escala'] * self.W
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=w)
            else:
                d.line([self._local(self.px(*q)) for q in catmull_rom(tr)], fill=255, width=w, joint='curve')
        return self._brillo(img, 7 * self.k, 0.45, 1.6)

    def _dibujar_sombra(self):
        """Silueta rellena en 0..1: la de la imagen descompuesta, o polígonos + trazos engrosados."""
        sil = self.cfg.get('silueta')
        if sil:
            # silueta en blanco sobre negro, o figura en gris con transparencia (de figura.py):
            # con figura_detalle, lo claro de la pintura queda más claro y las líneas oscuras se notan
            m = Image.open(io.BytesIO(base64.b64decode(sil['png'].split(',', 1)[1])))
            alfa, gris = (m.getchannel('A'), m.convert('L')) if 'A' in m.getbands() else (m.convert('L'), None)
            (xa, ya), (xb, yb) = self._local(self.px(sil['x'][0], sil['y'][1])), self._local(self.px(sil['x'][1], sil['y'][0]))
            tam, pos = (round(xb - xa), round(yb - ya)), (round(xa), round(ya))
            def colocar(c):
                img = Image.new('L', self._forma()[::-1], 0)
                img.paste(c.resize(tam, Image.LANCZOS), pos)
                return np.asarray(img.filter(ImageFilter.GaussianBlur(self.difuso)), np.float32) / 255
            capa = colocar(alfa)
            det = self.cfg.get('figura_detalle', 0) if gris is not None else 0
            if det > 0: capa *= (1 - det) + det * (0.35 + colocar(gris))
            return capa
        img = Image.new('L', self._forma()[::-1], 0)
        d = ImageDraw.Draw(img)
        grosor = round(1.4 * self.cfg['escala'] * self.W)
        for pol in self.cfg.get('sombra_relleno', []):
            d.polygon([self._local(self.px(*q)) for q in pol], fill=255)
        for tr in self.cfg['figura_trazos']:
            if not isinstance(tr[0], list):
                (cx, cy), r = self._local(self.px(tr[0], tr[1])), tr[2] * self.cfg['escala'] * self.W
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            else:
                d.line([self._local(self.px(*q)) for q in catmull_rom(tr)], fill=255, width=grosor, joint='curve')
        g = np.asarray(img.filter(ImageFilter.GaussianBlur(self.difuso)), np.float32) / 255
        return g / max(1e-6, g.max())

    def _dibujar_lineas(self, t):
        a, b = self.cfg['lineas']
        uniones = self.cfg['uniones']
        img = Image.new('L', self._forma()[::-1], 0)
        d = ImageDraw.Draw(img)
        hueco = 22 * self.k  # las líneas no tocan las estrellas
        paso = (b - a) / len(uniones)
        for j, (n1, n2) in enumerate(uniones):
            u = mas_suave((t - a - j * paso) / (paso * 2.5))
            if u <= 0: continue
            p, q = self.estrellas[n1]['pos'], self.estrellas[n2]['pos']
            v = q - p; L = np.linalg.norm(v); v = v / L
            p, q = p + v * hueco, q - v * hueco
            d.line([self._local(p), self._local(p + (q - p) * u)], fill=255, width=max(1, round(2.5 * self.k)))
        return self._brillo(img, 5 * self.k, 0.5, 1.4)

    def _estrella(self, capa, pos, amp, halo=1.0):
        k = self.k * self.cfg.get('estrellas_tamano', 1)
        sc, sh = k * (2.4 + 3.0 * amp), k * (9 + 18 * amp) * halo
        R = int(4 * sh) + 2
        x, y = pos[0] - self.x0, pos[1] - self.y0
        ix, iy = int(round(x)), int(round(y))
        ya, yb, xa, xb = max(0, iy - R), min(capa.shape[0], iy + R + 1), max(0, ix - R), min(capa.shape[1], ix + R + 1)
        if ya >= yb or xa >= xb: return
        gy, gx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
        dx, dy = gx - x, gy - y
        r2 = dx * dx + dy * dy
        v = np.exp(-r2 / (2 * sc * sc)) + 0.22 * np.exp(-r2 / (2 * sh * sh))
        # destello en cruz
        v += 0.18 * (np.exp(-dy * dy / (2 * k * k)) * np.exp(-np.abs(dx) / (sh * 1.3))
                     + np.exp(-dx * dx / (2 * k * k)) * np.exp(-np.abs(dy) / (sh * 1.3)))
        capa[ya:yb, xa:xb] += amp * v

    def capa(self, t):
        """Capa RGB (0..1) a sumar sobre el recorte en el tiempo t, o None si todavía no hay nada."""
        viaje = self.cfg['viaje']
        primera = min(s['fija'] for s in self.estrellas.values()) - viaje
        if t < primera: return None
        est = np.zeros(self._forma(), np.float32)
        dt_cuadro = 1 / self.cfg['fps']
        for s in self.estrellas.values():
            dt = t - s['fija']
            if dt < -viaje: continue
            if dt < 0:
                # viaje: sale del centro sobre el mismo rayo, acelera con la lluvia y frena al llegar
                for sub in range(3):  # desenfoque de movimiento
                    u = (dt + viaje - sub * dt_cuadro / 3) / viaje
                    pos = self.origen + (s['pos'] - self.origen) * (0.1 + 0.9 * mas_suave(u))
                    self._estrella(est, pos, s['amp'] * (0.25 + 0.55 * suave(u / 0.4)) / 3)
            else:
                destello = 2.2 * math.exp(-dt / 0.5)
                titileo = 1 + 0.06 * math.sin(2 * math.pi * 0.6 * t + s['fase'])
                brillo = self.cfg.get('estrellas_brillo', 1.15)
                self._estrella(est, s['pos'], s['amp'] * (brillo * titileo + destello), 1.25 + 0.8 * math.exp(-dt / 0.8))
        out = est[..., None] * COLOR_ESTRELLA

        if self.capa_sombra is not None:
            a, b = self.cfg['sombra']
            f = suave((t - a) / (b - a))
            if f > 0: out += self.cfg.get('sombra_brillo', 0.22) * f * self.capa_sombra[..., None] * COLOR_SOMBRA

        a, b = self.cfg['figura']
        f = suave((t - a) / (b - a))  # al aparecer la figura las líneas bajan un poco
        if f > 0: out += self.cfg.get('figura_brillo', 0.35) * f * self.capa_figura[..., None] * COLOR_FIGURA

        a, b = self.cfg['lineas']
        brillo = self.cfg.get('lineas_brillo', 0.5)
        if brillo > 0 and t >= a:
            if t > b + 3:
                if self.capa_lineas_final is None: self.capa_lineas_final = self._dibujar_lineas(b + 3)
                lin = self.capa_lineas_final
            else:
                lin = self._dibujar_lineas(t)
            out += brillo * (1 - 0.45 * f) * lin[..., None] * COLOR_LINEA

        return out

    def componer(self, cuadro, t):
        c = self.capa(t)
        if c is None: return cuadro
        rec = cuadro[self.y0:self.y1, self.x0:self.x1].astype(np.float32)
        rec += 255 * c
        cuadro[self.y0:self.y1, self.x0:self.x1] = np.clip(rec, 0, 255).astype(np.uint8)
        return cuadro


def leer(ruta, W):
    im = Image.open(ruta)
    im.draft('RGB', (W, W))  # el JPG se decodifica directo a 2048 en la prueba
    im = im.convert('RGB')
    if im.size != (W, W): im = im.resize((W, W), Image.LANCZOS)
    return np.array(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config')
    ap.add_argument('--prueba', action='store_true', help='2048 con el codificador del Mac (rápido)')
    ap.add_argument('--desde', type=float, default=0, help='segundo desde el que se renderiza')
    ap.add_argument('--hasta', type=float, default=None)
    ap.add_argument('--audio', help='música (se recorta al largo del video)')
    ap.add_argument('--salida')
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    carpeta = os.path.expanduser(cfg['secuencia'])
    cuadros = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
    # un cuadro que pesa mucho menos que sus vecinos está roto (casi negro): se usa el anterior
    pesos = [os.path.getsize(os.path.join(carpeta, f)) for f in cuadros]
    for i in range(1, len(cuadros)):
        vecinos = sorted(pesos[max(0, i - 5):i + 6])
        if pesos[i] < 0.3 * vecinos[len(vecinos) // 2]:
            print(f'Cuadro roto, se usa el anterior: {cuadros[i]}', file=sys.stderr)
            cuadros[i] = cuadros[i - 1]
    fps = cfg['fps']
    i0 = int(a.desde * fps)
    i1 = len(cuadros) if a.hasta is None else min(len(cuadros), int(a.hasta * fps))
    W = 2048 if a.prueba else 4096
    nombre = os.path.splitext(os.path.basename(a.config))[0]
    salida = a.salida or f'{nombre}-{W}{"-prueba" if a.prueba else ""}.mp4'

    cmd = ['ffmpeg', '-v', 'error', '-stats', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{W}',
           '-r', str(fps), '-i', '-']
    if a.audio: cmd += ['-ss', str(a.desde), '-i', a.audio]
    if a.prueba: cmd += ['-c:v', 'hevc_videotoolbox', '-b:v', '40M']
    else: cmd += ['-c:v', 'libx265', '-preset', 'slow', '-crf', '16', '-x265-params', 'log-level=error']
    cmd += ['-pix_fmt', 'yuv420p', '-tag:v', 'hvc1']
    if a.audio: cmd += ['-c:a', 'aac', '-b:a', '320k', '-shortest']
    cmd += [salida]

    con = Constelacion(cfg, W)
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    inicio = time.time()
    with ThreadPoolExecutor(6) as pool:
        cola = deque()
        sig = i0
        for i in range(i0, i1):
            while sig < i1 and len(cola) < 12:
                cola.append(pool.submit(leer, os.path.join(carpeta, cuadros[sig]), W)); sig += 1
            cuadro = con.componer(cola.popleft().result(), i / fps)
            ff.stdin.write(cuadro.tobytes())
            if i % fps == 0:
                print(f'\r{i / fps:6.1f} s  ({(i - i0 + 1) / (time.time() - inicio):.1f} cuadros/s)', end='', file=sys.stderr)
    ff.stdin.close()
    if ff.wait() != 0: sys.exit('ffmpeg falló')
    print(f'\nListo: {salida}', file=sys.stderr)


if __name__ == '__main__':
    main()
