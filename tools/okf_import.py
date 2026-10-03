"""設計書（機能設計書・契約書）から OKF を生成・更新する（試作）。

設計書の＊印の節（OKF から導出した情報）は読まない。正本となる情報
（属性の表、本文の節、使用データ・呼び出し・依存の表、配分、レビュー、管理情報）だけを読む。
ファイル名は <ID>.md、配置は structure/ と contracts/ の規約に従う。

使い方:
  python tools/okf_import.py <bundle> <設計書.md> [...]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from okf_io import write_concept  # noqa: E402

MISSING = {"【未記載】", "―", "なし", "該当なし", ""}
STATUS = {"作成中": "draft", "確定": "stable", "廃止": "deprecated"}
# 設計書の見出し → OKF 本文の節名（並びは OKF 本文の正規順）
BODY_SECTIONS = [("概要", "概要"), ("認証", "認証"), ("起動条件", "起動条件"), ("画面項目", "画面項目"),
                 ("操作・遷移", "操作・遷移"), ("処理内容", "処理"), ("設定内容", "設定"), ("エラー処理", "エラー"),
                 ("保持", "保持")]


def S(i):
    return f"/structure/{i}.md"


def C(i):
    return f"/contracts/{i}.md"


def sections(text, level):
    """指定レベルの見出しで分割し [(見出し, 本文)] を返す。コードブロック内は見出しとみなさない。"""
    out, cur, buf, fence = [], None, [], False
    mark = "#" * level + " "
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and re.match(r"^#{1,%d} " % level, line):
            if cur is not None:
                out.append((cur, "\n".join(buf).strip()))
            cur, buf = (line[len(mark):].strip() if line.startswith(mark) else None), []
            continue
        buf.append(line)
    if cur is not None:
        out.append((cur, "\n".join(buf).strip()))
    return [(h, b) for h, b in out if h is not None]


def heading_name(h):
    """「4.1.3 インターフェース＊」→「インターフェース＊」"""
    return re.sub(r"^[\d.]+\s*", "", h).strip()


def tables(text):
    """本文中の Markdown 表を [[{列: 値}]] で返す。"""
    out, rows = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif rows:
            out.append([dict(zip(rows[0], r)) for r in rows[2:]])
            rows = []
    return out


def row_attrs(text):
    """先頭の表（横 1 行または「項目・内容」の縦）を辞書にする。"""
    t = tables(text)
    if not t or not t[0]:
        return {}
    if set(t[0][0]) == {"項目", "内容"}:
        return {r["項目"]: r["内容"] for r in t[0]}
    return t[0][0]


def mgmt(text):
    m = re.search(r"管理情報：版 (\d+)／状態 (\S+)", text)
    return (int(m.group(1)), STATUS.get(m.group(2), m.group(2))) if m else (None, None)


def ids(s, prefix):
    return re.findall(rf"\b({prefix}-\d+)", s)


def parse_target(s):
    """「CMP-0402 データ基盤（全体）」→ component、「OBJ-a …、OBJ-b …」→ objects。"""
    objs = ids(s, "OBJ")
    return {"objects": [S(i) for i in objs]} if objs else {"component": S(ids(s, "CMP")[0])}


def number(v):
    f = float(v)
    return int(f) if f.is_integer() and "." not in str(v) else f


def num(v):
    return int(v) if v and str(v).isdigit() else v


def parse_uses(secs):
    out = []
    for r in (tables(secs.get("使用データ", "")) or [[]])[0]:
        u = {"contract": C(re.search(r"CTR-[FN]-\d+", r["契約"]).group(0)), "objects": [S(i) for i in ids(r["データ"], "OBJ")]}
        if r["CRUD"] not in MISSING:
            u["crud"] = r["CRUD"]
        u["rev"] = num(r["前提版"])
        out.append(u)
    for r in (tables(secs.get("呼び出し・依存", "")) or [[]])[0]:
        u = {"contract": C(re.search(r"CTR-[FN]-\d+", r["契約"]).group(0)), **parse_target(r["相手"]), "rev": num(r["前提版"])}
        out.append(u)
    return sorted(out, key=lambda u: u["contract"])


def import_object(heading, body):
    oid, title = re.match(r"^[\d.]+\s+(OBJ-\d+)\s+(.*)$", heading).groups()
    a = row_attrs(body.split("\n#### ", 1)[0])
    rev, status = mgmt(body)
    secs = {heading_name(h): b for h, b in sections(body, 4)}
    fm = {"type": "開発オブジェクト", "id": oid, "revision": rev, "title": title.strip(), "kind": a["種別"],
          "parent": S(ids(a["コンポーネント"], "CMP")[0]), "status": status, "operation": a.get("操作")}
    uses = parse_uses(secs)
    if uses:
        fm["uses"] = uses
    parts = [f"## {okf}\n\n{secs[doc]}" for doc, okf in BODY_SECTIONS if secs.get(doc) not in MISSING and doc in secs]
    return fm, "\n\n".join(parts)


def import_design(bundle, text):
    head = text.split("\n## ", 1)[0]
    sys_id, sys_title = re.match(r"^# 機能設計書\s+(SYS-\d+)\s+(.*)$", text.splitlines()[0]).groups()
    a = row_attrs(head)
    rev, status = mgmt(head)
    top = dict((heading_name(h), b) for h, b in sections(text, 2))
    written = []
    sys_fm = {"type": "システム", "id": sys_id, "revision": rev, "title": sys_title.strip(), "kind": a["種別"],
              "parent": S(ids(a["プロダクト"], "PRD")[0]), "status": status}
    overview = top.get("システム概要", "")
    written.append(write_concept(bundle / f"structure/{sys_id}.md", sys_fm, "" if overview in MISSING else overview))
    for r in tables(top.get("構成", ""))[0]:
        fm = {"type": "コンポーネント", "id": r["コンポーネントID"], "revision": num(r["版"]), "title": r["名称"],
              "kind": r["種別"], "parent": S(sys_id), "status": STATUS.get(r["状態"], r["状態"])}
        written.append(write_concept(bundle / f"structure/{fm['id']}.md", fm, "" if r["説明"] in MISSING else r["説明"]))
    for key in ("機能詳細", "データ詳細"):
        for heading, body in sections(top.get(key, ""), 3):
            fm, rest = import_object(heading, body)
            written.append(write_concept(bundle / f"structure/{fm['id']}.md", fm, rest))
    return written


def import_contract(bundle, text):
    a = row_attrs(text.split("\n## ", 1)[0])
    top = dict((heading_name(h), b) for h, b in sections(text, 2))
    func = a["種別"] == "機能契約"
    fm = {"type": a["種別"], "id": a["契約ID"], "revision": num(a["版"]), "title": a["契約名"]}
    if func:
        fm.update({"provider": S(ids(a["提供"], "CMP")[0]), "format": a.get("形式"),
                   "thickness": a.get("厚さ"), "resource": a.get("参照資料")})
    else:
        allocs = []
        for r in tables(top.get("配分", ""))[0]:
            al = {**parse_target(r["配分先"]), "value": r["配分"]}
            if r.get("数値") not in MISSING:
                al["amount"] = number(r["数値"])
            if r.get("合成") not in MISSING:
                al["role"] = r["合成"]
            if r.get("内包先") not in MISSING:
                al["within"] = next(iter(parse_target(r["内包先"]).values()))
                al["within"] = al["within"][0] if isinstance(al["within"], list) else al["within"]
            allocs.append(al)
        fm.update({"quality": a.get("品質特性"), "target": a.get("目標"),
                   "unit": a.get("単位"), "target_amount": number(a["目標値"]) if a.get("目標値") else None,
                   "allocations": allocs})
    fm["status"] = STATUS.get(a["状態"], a["状態"])
    review = tables(top.get("レビュー", ""))
    if review and review[0] and review[0][0].get("確認者"):
        r = review[0][0]
        fm["verified"] = {"by": r["確認者"], "at": r["確認日時"]}
    body = top.get("契約内容", "")
    return [write_concept(bundle / f"contracts/{fm['id']}.md", fm, "" if body in MISSING else body)]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    bundle = Path(sys.argv[1])
    for doc in sys.argv[2:]:
        text = Path(doc).read_text(encoding="utf-8")
        if text.startswith("# 機能設計書"):
            n = import_design(bundle, text)
        elif text.startswith("# 契約書"):
            n = import_contract(bundle, text)
        else:
            print(f"skip {doc}: 未対応の文書")
            continue
        print(f"{doc}: {sum(n)} / {len(n)} 件を更新")
