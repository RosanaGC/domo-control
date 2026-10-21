#!/bin/bash
cd "$(dirname "$0")"
PORT=8080
if ! command -v python3 >/dev/null 2>&1; then
  echo "Falta python3: instálalo con  xcode-select --install"
  read -r -p "Enter para cerrar"
  exit 1
fi
echo "Abriendo http://localhost:$PORT  (cierra esta ventana para detener)"
(sleep 1 && open "http://localhost:$PORT") &
python3 servidor.py $PORT
