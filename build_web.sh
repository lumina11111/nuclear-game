#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install --upgrade pygbag==0.9.3 fonttools 'qrcode[pil]'
python3 tools/prepare_web_fonts.py
python3 -m pygbag --build --archive --ume_block 1 --title '核境造物' .
echo '构建完成：build/web 与 build/web.zip'
