#!/usr/bin/env python3
"""Descompone una ilustración de constelación en datos para la capa Constelación.

De la imagen saca:
  - las estrellas (manchas muy brillantes), con un brillo según su tamaño,
  - las uniones (pares de estrellas con una línea clara entre ellas),
  - la silueta de la figura (más clara que el fondo), que queda dentro del .json como PNG.

  python3 descomponer.py orion.png                 # escribe orion.json al lado
  python3 descomponer.py orion.png --silueta 40    # umbral del canal verde para la silueta

Las coordenadas salen en "grados de cielo" (x a la derecha, y hacia arriba), centradas en la silueta,
con la escala de --alto: lo que miden las estrellas de arriba a abajo.
"""
import argparse, base64, io, json, os
import numpy as np
from PIL import Image, ImageFilter


def manchas(mask, minimo=1):
    """Componentes conexas (8 vecinos): lista de arrays (y, x)."""
    H, W = mask.shape
    visto = np.zeros_like(mask, bool)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if visto[y0, x0]: continue
        pila, pts = [(y0, x0)], []
        visto[y0, x0] = True
        while pila:
            y, x = pila.pop(); pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not visto[yy, xx]:
                        visto[yy, xx] = True; pila.append((yy, xx))
        if len(pts) >= minimo: out.append(np.array(pts))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('imagen')
    ap.add_argument('--salida')
    ap.add_argument('--estrella', type=float, default=215, help='brillo mínimo de una estrella (0-255)')
    ap.add_argument('--tam', type=int, default=5, help='tamaño mínimo de una estrella en píxeles (las chicas son del fondo)')
    ap.add_argument('--linea', type=float, default=150, help='verde mínimo de las líneas que unen estrellas')
    ap.add_argument('--silueta', type=float, default=40, help='verde mínimo de la silueta')
    ap.add_argument('--alto', type=float, default=31, help='grados de cielo que ocupan las estrellas de arriba a abajo')
    a = ap.parse_args()

    img = np.asarray(Image.open(a.imagen).convert('RGB')).astype(np.float32)
    H, W = img.shape[:2]
    lum, verde = img.mean(2), img[..., 1]

    # estrellas: el centro de cada mancha brillante; la más grande es la más brillante
    est = [(p[:, 1].mean(), p[:, 0].mean(), len(p)) for p in manchas(lum > a.estrella, a.tam)]
    est.sort(key=lambda e: -e[2])
    tmax, tmin = est[0][2], est[-1][2]
    mags = [0.3 + 3.2 * (tmax - t) / max(1, tmax - tmin) for _, _, t in est]

    # uniones: la línea entre dos estrellas es clara casi todo el camino y no pasa por otra estrella.
    # Las líneas son finas: se mira el máximo de cada píxel con sus vecinos.
    verde_v = np.asarray(Image.fromarray(verde.astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32)
    uniones = []
    for i in range(len(est)):
        for j in range(i + 1, len(est)):
            (x1, y1, _), (x2, y2, _) = est[i], est[j]
            L = np.hypot(x2 - x1, y2 - y1)
            u = np.linspace(0.15, 0.85, max(8, int(L)))
            xs, ys = np.round(x1 + (x2 - x1) * u).astype(int), np.round(y1 + (y2 - y1) * u).astype(int)
            if (verde_v[ys, xs] > a.linea).mean() < 0.8: continue
            entre = False
            for k, (x3, y3, _) in enumerate(est):
                if k in (i, j): continue
                t = ((x3 - x1) * (x2 - x1) + (y3 - y1) * (y2 - y1)) / (L * L)
                if 0 < t < 1 and np.hypot(x1 + t * (x2 - x1) - x3, y1 + t * (y2 - y1) - y3) < 4: entre = True; break
            if not entre: uniones.append((i, j))

    # silueta: la mancha clara más grande, sin agujeros, suavizada a 4× para que el borde no sea escalonado
    sil = max(manchas(verde > a.silueta, 50), key=len)
    m = np.zeros((H, W), bool); m[sil[:, 0], sil[:, 1]] = True
    fuera = np.zeros((H + 2, W + 2), bool); fuera[1:-1, 1:-1] = ~m
    borde = max(manchas(fuera), key=lambda p: ((p[:, 0] == 0) | (p[:, 1] == 0)).sum())
    lleno = np.ones((H + 2, W + 2), bool); lleno[borde[:, 0], borde[:, 1]] = False
    m = lleno[1:-1, 1:-1]
    k = 4
    big = Image.fromarray((m * 255).astype(np.uint8)).resize((W * k, H * k), Image.BICUBIC).filter(ImageFilter.GaussianBlur(k * 0.8))
    big = big.point(lambda v: 255 if v >= 128 else 0)
    buf = io.BytesIO(); big.save(buf, 'PNG', optimize=True)

    # a grados de cielo: centro en la silueta, escala por la altura de las estrellas
    ys_, xs_ = np.nonzero(m)
    cx, cy = (xs_.min() + xs_.max() + 1) / 2, (ys_.min() + ys_.max() + 1) / 2
    ey = [e[1] for e in est]
    s = (max(ey) - min(ey)) / a.alto
    gx = lambda x: round((x - cx) / s, 2)
    gy = lambda y: round((cy - y) / s, 2)
    nombres = [f'e{i + 1}' for i in range(len(est))]

    base = os.path.splitext(os.path.basename(a.imagen))[0]
    cfg = {
        '_ayuda': f'Generado por descomponer.py desde {os.path.basename(a.imagen)}. Coordenadas en grados de cielo (x a la derecha, y hacia arriba). '
                  'secuencia, fps y los tiempos los usa solo constelacion.py; en Domo Control se ajustan en la capa.',
        'secuencia': '~/Downloads/DESI_Y3P_push_4k', 'fps': 30,
        'centro': [0.5, 0.5], 'escala': 0.0125,
        'estrellas_inicio': 50, 'estrellas_fin': 90, 'viaje': 4, 'estrellas_tamano': 1.4,
        'lineas': [90, 98], 'lineas_brillo': 0.8,
        'sombra': [95, 107], 'sombra_brillo': 0.3, 'sombra_difuso': 0.15,
        'figura': [200, 201],
        'estrellas': [[n, gx(x), gy(y), round(mg, 2)] for n, (x, y, _), mg in zip(nombres, est, mags)],
        'uniones': [[nombres[i], nombres[j]] for i, j in uniones],
        'figura_trazos': [],
        'silueta': {'x': [gx(0), gx(W)], 'y': [gy(H), gy(0)], 'png': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()}
    }
    salida = a.salida or os.path.join(os.path.dirname(a.imagen) or '.', base + '.json')
    json.dump(cfg, open(salida, 'w'), ensure_ascii=False, indent=1)
    print(f'{salida}: {len(est)} estrellas, {len(uniones)} uniones, silueta {m.sum()} px ({len(buf.getvalue()) // 1024} KB)')


if __name__ == '__main__':
    main()
