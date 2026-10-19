#!/bin/bash
cd "$(dirname "$0")"
PORT=8080
echo "Abriendo http://localhost:$PORT  (cierra esta ventana para detener)"
(sleep 1 && open "http://localhost:$PORT") &
if command -v python3 >/dev/null 2>&1; then
  python3 -m http.server $PORT
else
  npx --yes serve -l $PORT .
fi
