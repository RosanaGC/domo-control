#!/usr/bin/env python3
"""Servidor local de Domo: sirve la app y guarda los proyectos en ./proyectos/<nombre>/.

Uso: python3 servidor.py [puerto]   (por defecto 8080). Solo acepta conexiones de este mismo equipo.

API (la usa Domo Control.html):
  GET    /api/proyectos                    lista de proyectos [{nombre, modificado}]
  PUT    /api/proyectos/<nombre>/<ruta>    guarda un archivo (proyecto.json, escenas/x.ply, musica/x.mp3…)
  DELETE /api/proyectos/<nombre>/<ruta>    borra un archivo del proyecto
Los archivos guardados se leen como estáticos en /proyectos/<nombre>/<ruta>.
"""
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(ROOT, 'proyectos')
API = '/api/proyectos'


def safe_path(parts):
    """Ruta dentro de proyectos/ o None si algún tramo intenta salirse."""
    for p in parts:
        if not p or p.startswith('.') or '/' in p or '\\' in p or '\0' in p:
            return None
    return os.path.join(PROJ, *parts)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def api_parts(self):
        path = urlparse(self.path).path
        if path != API and not path.startswith(API + '/'):
            return None
        return [unquote(x) for x in path[len(API):].split('/') if x]

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # proyecto.json cambia seguido: que el navegador no lo guarde en caché
        if urlparse(self.path).path.startswith('/proyectos/'):
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        parts = self.api_parts()
        if parts is None:
            return super().do_GET()
        if parts:
            return self.send_error(404)
        out = []
        if os.path.isdir(PROJ):
            for n in os.listdir(PROJ):
                f = os.path.join(PROJ, n, 'proyecto.json')
                if not n.startswith('.') and os.path.isfile(f):
                    out.append({'nombre': n, 'modificado': os.path.getmtime(f)})
        out.sort(key=lambda x: -x['modificado'])
        self.send_json(out)

    def do_PUT(self):
        parts = self.api_parts()
        dest = parts and len(parts) >= 2 and safe_path(parts)
        if not dest:
            return self.send_error(400, 'Ruta no válida')
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        n = int(self.headers.get('Content-Length') or 0)
        tmp = dest + '.parcial'
        # se escribe aparte y se renombra al final: si se corta, no queda un archivo a medias
        with open(tmp, 'wb') as f:
            while n > 0:
                b = self.rfile.read(min(n, 1 << 20))
                if not b:
                    break
                f.write(b)
                n -= len(b)
        if n:
            os.remove(tmp)
            return self.send_error(400, 'Archivo incompleto')
        os.replace(tmp, dest)
        self.send_json({'ok': True})

    def do_DELETE(self):
        parts = self.api_parts()
        dest = parts and len(parts) >= 2 and safe_path(parts)
        if not dest:
            return self.send_error(400, 'Ruta no válida')
        if os.path.isfile(dest):
            os.remove(dest)
        self.send_json({'ok': True})

    def log_message(self, fmt, *args):
        if self.command != 'GET':
            sys.stderr.write('%s %s\n' % (self.command, unquote(urlparse(self.path).path)))


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    os.makedirs(PROJ, exist_ok=True)
    print('Domo en http://localhost:%d  · proyectos en %s  (Ctrl+C para detener)' % (port, PROJ))
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
