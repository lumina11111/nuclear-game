# -*- coding: utf-8 -*-
"""下载并子集化网页所需的开源中文字体。

本脚本不会把完整字体长期保留在项目中，只根据当前源码出现的字符生成较小的
Noto Sans CJK SC 子集，供 Pygame/Pygbag 在浏览器中显示中文。
"""
from __future__ import annotations

import string
import tempfile
import urllib.request
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
FONT_DIR.mkdir(parents=True, exist_ok=True)

FONT_SOURCES = {
    "NotoSansCJKsc-Regular.otf": (
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/"
        "Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
    ),
    "NotoSansCJKsc-Bold.otf": (
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/"
        "Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf"
    ),
}
LICENSE_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/LICENSE"


def collect_characters() -> str:
    chars = set(string.printable)
    chars.update("，。！？；：、“”‘’（）【】《》—…℃×±≤≥→←↑↓·％‰")
    suffixes = {".py", ".txt", ".md", ".json", ".yml", ".yaml", ".bat", ".sh"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if "build" in path.parts or ".git" in path.parts:
            continue
        try:
            chars.update(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    return "".join(sorted(chars))


def subset_font(source: Path, target: Path, text: str) -> None:
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6]
    options.name_legacy = True
    options.name_languages = [0x409, 0x804]
    options.recalc_bounds = True
    options.recalc_timestamp = False
    font = subset.load_font(str(source), options)
    worker = subset.Subsetter(options=options)
    worker.populate(text=text)
    worker.subset(font)
    subset.save_font(font, str(target), options)


def download(url: str, target: Path) -> None:
    print(f"下载：{url}")
    request = urllib.request.Request(url, headers={"User-Agent": "nuclear-game-web-builder/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as file:
        file.write(response.read())


def main() -> None:
    text = collect_characters()
    print(f"需要保留 {len(text)} 个字符。")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        for filename, url in FONT_SOURCES.items():
            source = temp / filename
            target = FONT_DIR / filename
            download(url, source)
            subset_font(source, target, text)
            print(f"生成：{target}（{target.stat().st_size / 1024:.1f} KiB）")
    try:
        download(LICENSE_URL, FONT_DIR / "OFL-LICENSE.txt")
    except Exception as exc:
        print(f"字体许可证下载失败，不影响构建：{exc}")


if __name__ == "__main__":
    main()
