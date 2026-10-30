#!/usr/bin/env python3
"""Arma una constelación con una figura recortada (PNG con transparencia) y sus estrellas.

La figura aparece transparente, con los rasgos de la pintura (lo claro más claro, las líneas oscuras
se notan). Las estrellas y uniones vienen de un .json en píxeles de la imagen:

  {"estrellas": [["cabeza", 608, 420, 1.2], ...],   nombre, x, y, magnitud (menor = más brillante)
   "uniones": [["cabeza", "menton"], ...]}

Las estrellas se fijan en el orden de la lista.

  python3 figura.py buceo-figura.png buceo-puntos.json            # escribe buceo.json
  python3 figura.py buceo-figura.png buceo-puntos.json --alto 55  # figura más grande en el domo
"""
import argparse, base64, io, json, os
import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recorte', help='PNG con transparencia: la figura sola')
    ap.add_argument('puntos', help='.json con estrellas y uniones en píxeles de la imagen')
    ap.add_argument('--alto', type=float, default=50, help='grados de cielo que ocupa la figura de arriba a abajo')
    ap.add_argument('--max', type=int, default=1400, help='alto máximo en píxeles de la figura guardada')
    ap.add_argument('--salida')
    a = ap.parse_args()

    im = Image.open(a.recorte).convert('RGBA')
    x0, y0, x1, y1 = im.getbbox()
    fig = im.crop((x0, y0, x1, y1))
    # gris de la pintura + transparencia del recorte; se achica si es muy grande
    if fig.height > a.max: fig = fig.resize((round(fig.width * a.max / fig.height), a.max), Image.LANCZOS)
    la = Image.merge('LA', (fig.convert('L'), fig.getchannel('A')))
    buf = io.BytesIO(); la.save(buf, 'PNG', optimize=True)

    # a grados de cielo: centro en la figura, la altura de la figura es --alto
    s = (y1 - y0) / a.alto
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    gx = lambda x: round((x - cx) / s, 2)
    gy = lambda y: round((cy - y) / s, 2)
    p = json.load(open(a.puntos))
    nombres = {e[0] for e in p['estrellas']}
    for u in p.get('uniones', []):
        for n in u:
            if n not in nombres: raise SystemExit(f'La unión {u} nombra una estrella que no está: {n}')

    base = os.path.splitext(os.path.basename(a.puntos))[0].replace('-puntos', '')
    cfg = {
        '_ayuda': f'Generado por figura.py desde {os.path.basename(a.recorte)} y {os.path.basename(a.puntos)}. Coordenadas en grados de cielo '
                  '(x a la derecha, y hacia arriba). secuencia, fps y los tiempos los usa solo constelacion.py; en Domo Control se ajustan en la capa.',
        'secuencia': '~/Downloads/DESI_Y3P_push_4k', 'fps': 30,
        'centro': [0.5, 0.5], 'escala': 0.0125,
        'estrellas_inicio': 50, 'estrellas_fin': 90, 'viaje': 4, 'estrellas_tamano': 1.4,
        'lineas': [90, 98], 'lineas_brillo': 0.8,
        'sombra': [95, 107], 'sombra_brillo': 0.26, 'sombra_difuso': 0.08, 'figura_detalle': 0.6,
        'figura': [200, 201],
        'estrellas': [[n, gx(x), gy(y), m] for n, x, y, m in p['estrellas']],
        'uniones': p.get('uniones', []),
        'figura_trazos': [],
        'silueta': {'x': [gx(x0), gx(x1)], 'y': [gy(y1), gy(y0)], 'png': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()}
    }
    salida = a.salida or os.path.join(os.path.dirname(a.puntos) or '.', base + '.json')
    json.dump(cfg, open(salida, 'w'), ensure_ascii=False, indent=1)
    print(f'{salida}: {len(p["estrellas"])} estrellas, {len(cfg["uniones"])} uniones, figura {la.width}×{la.height} ({len(buf.getvalue()) // 1024} KB)')


if __name__ == '__main__':
    main()
