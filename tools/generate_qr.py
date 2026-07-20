# -*- coding: utf-8 -*-
"""根据已经发布的游戏网址生成二维码。"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="公开游戏网址，例如 https://name.github.io/repo/")
    parser.add_argument("-o", "--output", default="核境造物_扫码游玩.png")
    args = parser.parse_args()
    try:
        import qrcode
    except ImportError as exc:
        raise SystemExit("请先运行：python -m pip install qrcode[pil]") from exc
    image = qrcode.make(args.url)
    target = Path(args.output)
    image.save(target)
    print(f"二维码已生成：{target.resolve()}")


if __name__ == "__main__":
    main()
