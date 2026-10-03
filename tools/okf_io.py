"""OKF ファイルの正規形での読み書き（設計書との往復のための共通部品）。

正規形：
  ---
  <フロントマター：キー順は与えた順。辞書の配列は 1 行 1 要素のフロー形式>
  ---

  # <見出し>

  <本文>

使い方:
  python tools/okf_io.py <bundle> fmt    バンドル内の概念ファイルを正規形に書き直す
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
# 見出しを「<id>：<title>」に揃える種別（設計書から復元される概念）
CANONICAL_H1 = {"システム", "コンポーネント", "開発オブジェクト", "機能契約", "非機能契約"}


def scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    s = str(v)
    plain = (
        s
        and s == s.strip()
        and ": " not in s
        and " #" not in s
        and s[0] not in "-?:,[]{}#&*!|>'\"%@`"
        and not any(c in s for c in ",[]{}")
        and s.lower() not in ("true", "false", "null", "yes", "no", "on", "off", "~")
        and not re.fullmatch(r"[-+]?\d[\d.eE+-]*", s)
    )
    return s if plain else json.dumps(s, ensure_ascii=False)


def flow(v):
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {flow(x)}" for k, x in v.items()) + " }"
    if isinstance(v, list):
        return "[" + ", ".join(flow(x) for x in v) + "]"
    return scalar(v)


def dump_frontmatter(fm):
    lines = []
    for k, v in fm.items():
        if k.startswith("_") or v is None:
            continue
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            lines.append(f"{k}:")
            lines += [f"  - {flow(x)}" for x in v]
        elif isinstance(v, (list, dict)):
            lines.append(f"{k}: {flow(v)}")
        else:
            lines.append(f"{k}: {scalar(v)}")
    return "\n".join(lines) + "\n"


def split_file(text):
    """(生のフロントマター dict, 見出し, 見出し以降の本文) に分ける。"""
    _, fm, body = text.split("---", 2)
    fm = yaml.safe_load(fm) or {}
    body = body.strip()
    h1 = None
    if body.startswith("# "):
        h1, _, body = body.partition("\n")
        h1 = h1[2:].strip()
    return fm, h1, body.strip()


def render_file(fm, h1, rest):
    out = "---\n" + dump_frontmatter(fm) + "---\n\n" + f"# {h1}\n"
    return out + (f"\n{rest.strip()}\n" if rest and rest.strip() else "")


def canonical_h1(fm, h1):
    if fm.get("type") in CANONICAL_H1:
        return f"{fm['id']}：{fm['title']}"
    return h1 or f"{fm.get('id')}：{fm.get('title')}"


def write_concept(path: Path, fm, rest):
    """概念ファイルを書く。既存ファイルがあれば、新しい fm にないキー（設計書に現れないリレーション等）は残す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old, _, _ = split_file(path.read_text(encoding="utf-8"))
        merged = {k: fm.get(k, v) if k in fm else v for k, v in old.items()}
        merged.update({k: v for k, v in fm.items() if k not in old})
        fm = {k: v for k, v in merged.items() if v is not None}
    text = render_file(fm, canonical_h1(fm, None), rest)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def fmt(bundle: Path):
    changed = []
    for p in sorted(bundle.rglob("*.md")):
        if p.name in RESERVED:
            continue
        text = p.read_text(encoding="utf-8")
        fm, h1, rest = split_file(text)
        if fm.get("uses"):
            fm["uses"] = sorted(fm["uses"], key=lambda u: u["contract"])
        new = render_file(fm, canonical_h1(fm, h1), rest)
        if new != text:
            p.write_text(new, encoding="utf-8", newline="\n")
            changed.append(p)
    return changed


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[2] == "fmt":
        for p in fmt(Path(sys.argv[1])):
            print("fmt", p)
