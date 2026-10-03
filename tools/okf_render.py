"""OKF バンドルから人・SDD ツール向けの文書を生成する（試作）。

OKF は AI が間違えないための正本。ここで生成する文書は出力物であり、手で編集しない。

使い方:
  python tools/okf_render.py <bundle> spec <REQ-id>     SDD Spec（spec-kit の spec.md 相当）
  python tools/okf_render.py <bundle> design <SYS-id>   機能設計書（システム単位）
  python tools/okf_render.py <bundle> contract <CTR-id> 契約書（契約単位のレビュー）
"""
import re
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from okf_check import DATA_KINDS, allocated_to, by_type, contract_refs, crud_of, load, targets  # noqa: E402
from okf_io import scalar  # noqa: E402

MISSING = "【未記載】"


def section(body, name):
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else ""


def code_blocks(body):
    return re.findall(r"```(\w*)\n(.*?)```", body, re.S)


def by_id(nodes):
    return {n["id"]: n for n in nodes.values() if n.get("id")}


def label(n):
    return f"{n['id']} {n['title']}"


def ref_target_label(nodes, ref):
    if ref.get("component"):
        return "コンポーネント：" + label(nodes[ref["component"]])
    if ref.get("objects"):
        return "開発オブジェクト：" + "、".join(label(nodes[o]) for o in ref["objects"])
    return "（契約全体）"


def is_data(nodes, path):
    return nodes[path].get("kind") in DATA_KINDS


def children(nodes, parent):
    return [n for n in nodes.values() if n.get("parent") == parent]


def system_of(nodes, path):
    n = nodes[path]
    while n.get("type") != "システム":
        n = nodes[n["parent"]]
    return n


def writers_missing(nodes, data_paths):
    out = []
    for d in data_paths:
        if not any(set(v) & set("CU") for v in crud_of(nodes, d).values()):
            out.append(d)
    return out


# ---------------------------------------------------------------- SDD Spec


def gwt(text):
    """受入基準の「前提／操作／結果」を Given/When/Then に寄せる。"""
    return (text.replace("**前提**", "**Given**").replace("**操作**", "**When**").replace("**結果**", "**Then**"))


def implementing_objects(nodes, specs):
    """要件群を実装する開発オブジェクト（データは除く）。"""
    out = []
    for s in specs:
        for ref in s.get("contracts") or []:
            c = nodes[ref["contract"]]
            if c["type"] != "機能契約":
                continue
            if ref.get("component"):
                out += [o["_path"] for o in children(nodes, ref["component"])]
            out += [t for t in ref.get("objects") or [] if not is_data(nodes, t)]
            # 非データ契約は利用側も実装対象になる
            if not all(is_data(nodes, t) for t in targets(ref)) or ref.get("component"):
                for o in by_type(nodes, "開発オブジェクト"):
                    if any(u["contract"] == c["_path"] for u in o.get("uses") or []):
                        out.append(o["_path"])
    return [nodes[p] for p in dict.fromkeys(out)]


def usecase_screens(items):
    return list(dict.fromkeys(u["screen"] for n in items for u in n.get("usecase") or [] if u.get("screen")))


def spec_structure(nodes, specs, req=None):
    """Spec が関わる Structure の対象と役割、関わる契約を集める。"""
    roles, contracts = {}, {}

    def add(path, role):
        roles.setdefault(path, [])
        if role not in roles[path]:
            roles[path].append(role)

    func = [s for s in specs if s.get("category") == "機能"]
    implementers = implementing_objects(nodes, func)
    for o in implementers:
        add(o["_path"], "実装")
    # ユースケース（補足）に出てくる画面。作る対象なので依存もたどる
    for sc in usecase_screens(([req] if req else []) + specs):
        add(sc, "ユースケース")
        if nodes[sc] not in implementers:
            implementers.append(nodes[sc])
    for s in specs:
        for ref in s.get("contracts") or []:
            c = nodes[ref["contract"]]
            contracts.setdefault(c["_path"], c)
            if c.get("provider"):
                add(c["provider"], f"提供（{c['id']}）")
            for t in targets(ref):
                if nodes[t]["type"] == "開発オブジェクト" and is_data(nodes, t):
                    add(t, "データ")
            for a in c.get("allocations") or []:
                if a.get("component"):
                    add(a["component"], f"配分（{c['id']}：{a['value']}）")
                    for o in children(nodes, a["component"]):
                        add(o["_path"], f"配分（{c['id']}）")
                for o in a.get("objects") or []:
                    add(o, f"配分（{c['id']}：{a['value']}）")
    # 実装する開発オブジェクトが利用する契約の先（1 段）
    for o in implementers:
        for u in o.get("uses") or []:
            c = nodes[u["contract"]]
            contracts.setdefault(c["_path"], c)
            add(c["provider"], f"提供（{c['id']}）")
            dep = [x["_path"] for x in children(nodes, u["component"])] if u.get("component") else u["objects"]
            for d in dep:
                if "実装" not in roles.get(d, []):
                    add(d, f"依存（{c['id']}" + (f"・{u['crud']}" if u.get("crud") else "") + "）")
    # 祖先（コンポーネント・システム・プロダクト）を補う
    for path in list(roles):
        n = nodes[path]
        while n.get("parent"):
            roles.setdefault(n["parent"], [])
            n = nodes[n["parent"]]
    return roles, contracts


def structure_tree(nodes, roles):
    def walk(path, depth):
        n = nodes[path]
        r = "　— " + "、".join(roles[path]) if roles[path] else ""
        kind = f"（{n['kind']}）" if n.get("kind") else ""
        out = [f"{'  ' * depth}- {n['type']} {label(n)}{kind}{r}"]
        for c in sorted((c for c in children(nodes, path) if c["_path"] in roles), key=lambda c: c["id"]):
            out += walk(c["_path"], depth + 1)
        return out
    tops = [p for p in roles if not nodes[p].get("parent")]
    return [line for p in tops for line in walk(p, 0)]


def render_spec(nodes, req_id):
    ids = by_id(nodes)
    req = ids[req_id]
    specs = [s for s in by_type(nodes, "要件") if req["_path"] in (s.get("from") or [])]
    func = [s for s in specs if s.get("category") == "機能"]
    nonfunc = [s for s in specs if s.get("category") != "機能"]
    wishes = [nodes[w] for w in req.get("from") or []]
    clar = []

    L = [
        f"# Feature Specification: {req['title']}",
        "",
        f"**Feature ID**: {req_id}  ",
        f"**Status**: {req.get('status', 'draft')}  ",
        f"**Generated**: {date.today().isoformat()}（OKF バンドルから生成。手で編集しない）",
        "",
        "## Traceability（要望・要求・要件）",
        "",
        "### 要望",
        "",
        "| ID | 要望 | 出典（裁定） |",
        "|---|---|---|",
        *[f"| {w['id']} | {w['title']} | {'、'.join(label(nodes[r]) for r in w.get('from') or []) or '―'} |" for w in wishes],
        "",
        "### 要求",
        "",
        "| ID | 要求 | 由来する要望 |",
        "|---|---|---|",
        f"| {req_id} | {req['title']} | {'、'.join(w['id'] for w in wishes)} |",
        "",
        "### 要件",
        "",
        "| ID | 区分 | 要件 | 他に由来する要求 | 契約 → 参照先 |",
        "|---|---|---|---|---|",
    ]
    for s in specs:
        others = [nodes[r]["id"] for r in s.get("from") or [] if r != req["_path"]]
        refs = "<br>".join(f"{nodes[r['contract']]['id']} → {ref_target_label(nodes, r)}" for r in s.get("contracts") or [])
        L.append(f"| {s['id']} | {s['category']} | {s['title']} | {'、'.join(others) or '―'} | {refs} |")

    L += ["", "## User Scenarios & Testing *(mandatory)*", "", f"### User Story 1 - {req['title']}", "",
          req["title"] + "。", ""]
    steps = [(n, u) for n in [req] + specs for u in n.get("usecase") or []]
    if steps:
        L += ["**Use Case**（補足）：", ""]
        L += [f"{i}. {u['step']}" + (f"（画面：{label(nodes[u['screen']])}）" if u.get("screen") else "") + (f" ※{n['id']}" if n is not req else "")
              for i, (n, u) in enumerate(steps, 1)]
        L += [""]
    L += ["**Acceptance Scenarios**：", ""]
    for s in func:
        ac = section(s["_body"], "受入基準")
        if not ac:
            clar.append(f"{s['id']} の受入基準がない")
        L += [f"*{label(s)}*", "", gwt(ac) or f"[NEEDS CLARIFICATION: {s['id']} の受入基準]", ""]

    L += ["## Requirements *(mandatory)*", "", "### Functional Requirements", ""]
    L += [f"- **FR-{i:03}**（{s['id']}）：{s['title']}" for i, s in enumerate(func, 1)] or ["- なし"]

    roles, contracts = spec_structure(nodes, specs, req)
    entities = [p for p, r in roles.items() if nodes[p]["type"] == "開発オブジェクト" and is_data(nodes, p)]
    L += ["", "### Key Entities", ""]
    L += [f"- **{nodes[e]['title']}**（{nodes[e]['id']}）— {'、'.join(roles[e])}" for e in entities] or ["- なし"]
    for e in writers_missing(nodes, entities):
        clar.append(f"{nodes[e]['title']}（{nodes[e]['id']}）を登録・更新する要件・開発オブジェクトがない")

    L += ["", "## Success Criteria *(mandatory)*", "", "### Measurable Outcomes", ""]
    for i, s in enumerate(nonfunc, 1):
        L += [f"- **SC-{i:03}**（{s['id']}）：{s['title']}"]
        L += ["  " + line for line in section(s["_body"], "受入基準").splitlines()]
    if not nonfunc:
        L += ["- なし"]

    L += ["", "## Structure（対象の全体）", "",
          "役割：実装＝この Spec で作る／ユースケース＝補足のユースケースに出てくる画面／データ＝要件が参照するデータ／依存＝実装が利用する契約の先／"
          "提供＝関わる契約の提供コンポーネント／配分＝非機能の配分先", ""]
    L += structure_tree(nodes, roles)

    L += ["", "## Contracts（関わる契約）", "", "| 契約 | 種別 | 提供 / 目標 |", "|---|---|---|"]
    for c in contracts.values():
        what = label(nodes[c["provider"]]) if c.get("provider") else c.get("target", "")
        L.append(f"| {label(c)} | {c['type']} | {what} |")

    L += ["", "## Open Questions", ""]
    L += [f"- [NEEDS CLARIFICATION: {c}]" for c in clar] or ["- なし"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 機能設計書


def related_specs(nodes, obj):
    """開発オブジェクトに関係する要件。直接：契約参照の先が自分か自分のコンポーネント。
    利用：自分が利用する非データ契約を、要件も同じ範囲で参照している。"""
    out = {}
    uses = obj.get("uses") or []
    for s in by_type(nodes, "要求") + by_type(nodes, "要件"):
        if obj["_path"] in usecase_screens([s]):
            out.setdefault(s["_path"], "ユースケース")
    for s in by_type(nodes, "要件"):
        for ref in s.get("contracts") or []:
            if any(allocated_to(a, obj) for a in nodes[ref["contract"]].get("allocations") or []):
                out.setdefault(s["_path"], "配分")
            ts = targets(ref)
            if obj["_path"] in ts or obj["parent"] in ts:
                out.setdefault(s["_path"], "直接")
            for u in uses:
                if u["contract"] != ref["contract"] or all(is_data(nodes, t) for t in targets(u)):
                    continue
                if ref.get("component") or set(ts) & set(targets(u)):
                    out.setdefault(s["_path"], "利用")
    return [(nodes[p], how) for p, how in out.items()]


DERIVED = "＊"
DERIVED_NOTE = ("凡例：＊印の節は OKF から自動で導出した参考情報で、設計書から OKF への取り込み対象外。"
                "トレーサビリティの「直接」は要件が契約で直接指す、「利用」は利用する契約経由、「配分」は非機能の配分、「ユースケース」は要求・要件の補足に登場。")
STATUS_JA = {"draft": "作成中", "stable": "確定", "deprecated": "廃止"}

# 種別ごとの本文の節（設計書の見出し, OKF の節名）。並びは OKF 本文の正規順。
BODY_SECTIONS = [("概要", "概要"), ("認証", "認証"), ("起動条件", "起動条件"), ("画面項目", "画面項目"),
                 ("操作・遷移", "操作・遷移"), ("処理内容", "処理"), ("設定内容", "設定"), ("エラー処理", "エラー"),
                 ("保持", "保持")]
REQUIRED = {
    "API": ["概要", "認証", "処理", "エラー"],
    "画面": ["概要", "画面項目", "操作・遷移", "エラー"],
    "イベント処理": ["概要", "起動条件", "処理", "エラー"],
    "バックグラウンド処理": ["概要", "起動条件", "処理", "エラー"],
    "IaCリソース": ["概要", "設定"],
    "テーブル": ["概要", "保持"],
    "ファイル": ["概要", "保持"],
}
OKF_TO_DOC = {okf: doc for doc, okf in BODY_SECTIONS}


def body_rest(n):
    """見出し（# ...）を除いた本文。"""
    body = n["_body"].strip()
    if body.startswith("# "):
        body = body.partition("\n")[2]
    return body.strip()


def attr_table(rows):
    return ["| 項目 | 内容 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows if v not in (None, "")]


def row_table(cols):
    """属性を 1 行の横長の表で出す。"""
    cols = [(k, v) for k, v in cols if v not in (None, "")]
    return ["| " + " | ".join(k for k, _ in cols) + " |", "|" + "---|" * len(cols), "| " + " | ".join(str(v) for _, v in cols) + " |"]


def mgmt(n):
    return f"管理情報：版 {n.get('revision')}／状態 {STATUS_JA.get(n.get('status'), n.get('status'))}"


def short_target(nodes, ref):
    if ref.get("component"):
        return label(nodes[ref["component"]]) + "（全体）"
    return "、".join(label(nodes[o]) for o in ref.get("objects") or [])


def split_uses(nodes, o):
    uses = sorted(o.get("uses") or [], key=lambda u: u["contract"])
    data = [u for u in uses if u.get("objects") and all(is_data(nodes, t) for t in u["objects"])]
    other = [u for u in uses if u not in data]
    return data, other


def data_table(nodes, uses):
    out = ["| データ | CRUD | 契約 | 前提版 |", "|---|---|---|---|"]
    for u in uses:
        names = "、".join(label(nodes[t]) for t in u["objects"])
        out.append(f"| {names} | {u.get('crud') or '―'} | {label(nodes[u['contract']])} | {u.get('rev')} |")
    return out


def calls_table(nodes, uses):
    out = ["| 契約 | 相手 | 前提版 |", "|---|---|---|"]
    for u in uses:
        out.append(f"| {label(nodes[u['contract']])} | {short_target(nodes, u)} | {u.get('rev')} |")
    return out


def flatten_schema(schema, prefix="", required=()):
    """OpenAPI のスキーマを「項目・型・必須・備考」の行に平らにする。"""
    rows = []
    for name, prop in (schema.get("properties") or {}).items():
        path = f"{prefix}{name}"
        typ = prop.get("type") or ("列挙" if prop.get("enum") else "")
        note = []
        if prop.get("enum"):
            note.append("／".join(map(str, prop["enum"])))
        if prop.get("format"):
            note.append(prop["format"])
        if typ == "array":
            items = prop.get("items") or {}
            rows.append((path, f"{items.get('type', 'object')} の配列", "○" if name in required else "", "、".join(note)))
            rows += flatten_schema(items, path + "[].", items.get("required") or ())
            continue
        rows.append((path, typ, "○" if name in required else "", "、".join(note)))
        if prop.get("properties"):
            rows += flatten_schema(prop, path + ".", prop.get("required") or ())
    return rows


def openapi_tables(op):
    L = []
    params = op.get("parameters") or []
    if params:
        L += ["**パラメータ**", "", "| 名前 | 位置 | 型 | 必須 |", "|---|---|---|---|"]
        L += [f"| {p['name']} | {p.get('in', '')} | {(p.get('schema') or {}).get('type', 'string')} | {'○' if p.get('required') else ''} |" for p in params]
        L += [""]
    for media, spec in ((op.get("requestBody") or {}).get("content") or {}).items():
        schema = (spec or {}).get("schema")
        if schema:
            L += [f"**入力**（{media}）", "", "| 項目 | 型 | 必須 | 備考 |", "|---|---|---|---|"]
            L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in flatten_schema(schema, required=schema.get("required") or ())]
        else:
            L += [f"**入力**：{media}"]
        L += [""]
    resps = op.get("responses") or {}
    if resps:
        L += ["**出力**", "", "| コード | 内容 |", "|---|---|"]
        for code, r in resps.items():
            r = r or {}
            desc = r.get("description", "")
            for media, spec in (r.get("content") or {}).items():
                schema = (spec or {}).get("schema") or {}
                if schema.get("type") == "array":
                    fields = "、".join((schema.get("items") or {}).get("properties", {}).keys())
                    desc = (desc + " " if desc else "") + f"配列（{fields}）"
                elif schema.get("properties"):
                    desc = (desc + " " if desc else "") + "、".join(schema["properties"].keys())
            L.append(f"| {code} | {desc or '（本文の定義なし）'} |")
        L += [""]
    return L


def interface_of(nodes, obj):
    """開発オブジェクトのインターフェース（契約から導出）。"""
    comp = nodes[obj["parent"]]
    provided = [c for c in by_type(nodes, "機能契約") if c.get("provider") == comp["_path"]]
    if obj.get("operation"):
        method, path = obj["operation"].split(" ", 1)
        for c in provided:
            for lang, code in code_blocks(c["_body"]):
                if lang != "yaml":
                    continue
                spec = yaml.safe_load(code) or {}
                op = (spec.get("paths") or {}).get(path, {}).get(method.lower())
                if op is not None:
                    return "\n".join([f"出典：{label(c)}", ""] + openapi_tables(op)).strip()
        return ""
    if obj.get("kind") == "画面":
        uses = [u for u in obj.get("uses") or [] if not all(is_data(nodes, t) for t in targets(u))]
        return ("呼び出す API：" + "、".join(short_target(nodes, u) for u in uses)) if uses else ""
    for c in provided:
        blocks = code_blocks(c["_body"])
        if blocks:
            what = "提供する接続情報" if obj.get("kind") == "IaCリソース" else "受信するメッセージ"
            return f"{what}（出典：{label(c)}）\n\n" + "\n".join(f"```{l}\n{b}```" for l, b in blocks)
    return ""


def er_columns(nodes, data):
    """データ（テーブル）の項目定義を、提供する契約の ER 図から取り出す。"""
    entity = data["title"].removesuffix("テーブル")
    for c in by_type(nodes, "機能契約"):
        if c.get("provider") != data["parent"]:
            continue
        for lang, code in code_blocks(c["_body"]):
            if lang != "mermaid" or "erDiagram" not in code:
                continue
            m = re.search(rf"^\s*{re.escape(entity)}\s*\{{\n(.*?)^\s*\}}", code, re.M | re.S)
            if m:
                rows = [f"| {p[1]} | {p[0]} | {' '.join(p[2:])} |" for p in (l.split() for l in m.group(1).strip().splitlines()) if len(p) >= 2]
                return [f"出典：{label(c)} の ER 図", "", "| 項目 | 型 | キー |", "|---|---|---|"] + rows
    return []


def numbered(prefix):
    n = 0

    def nxt(title):
        nonlocal n
        n += 1
        return f"#### {prefix}.{n} {title}"
    return nxt


def body_sections(o, gaps):
    """種別ごとの本文の節 [(見出し, 本文)]。書かれている節だけを返し、必須で抜けている節は gaps に積む。"""
    out = []
    req = REQUIRED.get(o.get("kind"), ["概要"])
    for doc_name, okf_name in BODY_SECTIONS:
        text = section(o["_body"], okf_name)
        if text:
            out.append((doc_name, text))
        elif okf_name in req:
            gaps.setdefault(o["id"], []).append(doc_name)
    return out


def render_object(nodes, o, num, gaps, itf_missing):
    h = numbered(num)
    L = ["", f"### {num} {o['id']} {o['title']}", ""]
    L += row_table([("種別", o["kind"]), ("コンポーネント", label(nodes[o["parent"]])), ("操作", o.get("operation"))])
    L += [""]
    secs = body_sections(o, gaps)
    # 概要の直後にインターフェース（導出）を置く
    if secs and secs[0][0] == "概要":
        L += [h("概要"), "", secs[0][1], ""]
        secs = secs[1:]
    itf = interface_of(nodes, o)
    if itf:
        L += [h(f"インターフェース{DERIVED}"), "", itf, ""]
    elif o.get("kind") in ("API", "イベント処理"):
        itf_missing.append(o["id"])
    if o.get("kind") in DATA_KINDS:
        cols = er_columns(nodes, o)
        if cols:
            L += [h(f"項目定義{DERIVED}"), ""] + cols + [""]
    for name, text in secs:
        L += [h(name), "", text, ""]
    data, other = split_uses(nodes, o)
    if data:
        L += [h("使用データ"), ""] + data_table(nodes, data) + [""]
    if other:
        L += [h("呼び出し・依存"), ""] + calls_table(nodes, other) + [""]
    if o.get("kind") not in DATA_KINDS:
        rs = related_specs(nodes, o)
        nf = [(c, a) for c in by_type(nodes, "非機能契約") for a in c.get("allocations") or [] if allocated_to(a, o)]
        L += [h(f"トレーサビリティ{DERIVED}"), ""]
        L += [f"- {s['id']} {s['title']}（{how}）" for s, how in rs] or ["- 関連する要求・要件なし"]
        L += [f"- 非機能 {c['id']} {c['title']}：{a['value']}" for c, a in nf]
        L += [""]
    L += [mgmt(o)]
    return L


def render_design(nodes, sys_id):
    """機能設計書。設計書から OKF を復元できるよう、正本となる情報は表と見出しで必ず出す。
    ＊印の節は OKF から計算したもので、取り込み時には読まない。"""
    ids = by_id(nodes)
    system = ids[sys_id]
    product = nodes[system["parent"]]
    comps = sorted(children(nodes, system["_path"]), key=lambda c: c["id"])
    objs = [o for c in comps for o in sorted(children(nodes, c["_path"]), key=lambda o: o["id"])]
    funcs = [o for o in objs if o.get("kind") not in DATA_KINDS]
    datas = [o for o in objs if o.get("kind") in DATA_KINDS]
    gaps, itf_missing, notes = {}, [], []

    L = [f"# 機能設計書　{sys_id} {system['title']}", ""]
    L += row_table([("種別", system.get("kind")), ("プロダクト", label(product)), ("作成日", date.today().isoformat())])
    L += ["", mgmt(system), "", DERIVED_NOTE, "", "## 1. システム概要", "", body_rest(system) or MISSING, "", "## 2. 構成", "",
          "| コンポーネントID | 名称 | 種別 | 説明 | 版 | 状態 |", "|---|---|---|---|---|---|"]
    for c in comps:
        L.append(f"| {c['id']} | {c['title']} | {c['kind']} | {body_rest(c) or '―'} | {c.get('revision')} | {STATUS_JA.get(c.get('status'), c.get('status'))} |")

    L += ["", f"## 3. 機能一覧{DERIVED}", ""]
    if funcs:
        L += ["| 機能ID | 機能名 | 種別 | 操作 | コンポーネント |", "|---|---|---|---|---|"]
        L += [f"| {o['id']} | {o['title']} | {o['kind']} | {o.get('operation') or '―'} | {nodes[o['parent']]['title']} |" for o in funcs]
    else:
        L += ["該当なし"]

    L += ["", "## 4. 機能詳細"]
    for i, o in enumerate(funcs, 1):
        L += render_object(nodes, o, f"4.{i}", gaps, itf_missing)
    if not funcs:
        L += ["", "該当なし"]

    L += ["", "## 5. データ詳細"]
    for i, d in enumerate(datas, 1):
        L += render_object(nodes, d, f"5.{i}", gaps, itf_missing)
    if not datas:
        L += ["", "該当なし"]

    data_paths = list(dict.fromkeys(t for o in funcs for u in o.get("uses") or [] for t in targets(u) if is_data(nodes, t)))
    if data_paths:
        L += ["", f"## 6. CRUD 図{DERIVED}", "",
              "| 機能 ＼ データ | " + " | ".join(nodes[d]["title"] for d in data_paths) + " |",
              "|---|" + "---|" * len(data_paths)]
        for o in funcs:
            row = [crud_of(nodes, d).get(o["_path"], "") for d in data_paths]
            if any(row):
                L.append(f"| {o['title']} | " + " | ".join(row) + " |")
    for d in writers_missing(nodes, [o["_path"] for o in datas]):
        notes.append(f"{label(nodes[d])} を登録・更新する機能がない（要件の抜けの可能性）")

    comp_paths = {c["_path"] for c in comps}
    ext = {}
    for o in by_type(nodes, "開発オブジェクト"):
        for u in o.get("uses") or []:
            c = nodes[u["contract"]]
            if c.get("provider") in comp_paths and o["parent"] not in comp_paths:
                ext.setdefault(("提供", c["_path"]), set()).add(f"{system_of(nodes, o['_path'])['title']}（{o['title']}）")
            elif o["parent"] in comp_paths and c.get("provider") not in comp_paths:
                ext.setdefault(("利用", c["_path"]), set()).add(f"{system_of(nodes, c['provider'])['title']}（{o['title']} から）")
    if ext:
        L += ["", f"## 7. 外部インターフェース{DERIVED}", "", "| 方向 | 契約 | 相手 |", "|---|---|---|"]
        L += [f"| {d} | {label(nodes[c])} | {'<br>'.join(sorted(s))} |" for (d, c), s in sorted(ext.items(), key=lambda x: (x[0][0], x[0][1]))]

    obj_paths = {o["_path"] for o in objs}
    nfr = {}
    for c in by_type(nodes, "非機能契約"):
        for a in c.get("allocations") or []:
            if a.get("component") in comp_paths or set(a.get("objects") or []) & obj_paths:
                nfr.setdefault(c["_path"], []).append(a)
    if nfr:
        L += ["", f"## 8. 非機能要件{DERIVED}"]
        for cp, allocs in nfr.items():
            c = nodes[cp]
            L += ["", f"**{label(c)}**（目標：{c['target']}）", ""]
            L += [f"- {short_target(nodes, a)}：{a['value']}" for a in allocs]

    L += ["", f"## 9. 未記載・確認事項{DERIVED}", ""]
    if gaps:
        cols = [d for d, _ in BODY_SECTIONS if any(d in v for v in gaps.values())]
        L += ["本書で記入する節：", "", "| 機能・データ | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
        for oid, v in gaps.items():
            L.append(f"| {label(ids[oid])} | " + " | ".join("未" if c in v else "" for c in cols) + " |")
        L += [""]
    if itf_missing:
        L += ["契約側で補う：", ""] + [f"- {label(ids[i])} のインターフェースが契約に定義されていない" for i in itf_missing] + [""]
    if notes:
        L += ["その他：", ""] + [f"- {n}" for n in notes] + [""]
    if not (gaps or itf_missing or notes):
        L += ["なし"]
    return "\n".join(L).rstrip() + "\n"


# ---------------------------------------------------------------- 契約書（契約単位のレビュー）


def reconcile(nodes, c):
    """契約内容と提供コンポーネント配下の開発オブジェクトの突合。
    契約に主従はないため、差異はどちらかを正として機械的に直さず、裁定の材料として示す。"""
    objs = children(nodes, c["provider"])
    out = []
    blocks = code_blocks(c["_body"])
    ents = set()
    for lang, code in blocks:
        if lang == "mermaid" and "erDiagram" in code:
            for line in code.splitlines():
                m = re.match(r"\s*([^\s{|}]+)\s*\{\s*$", line)
                if m:
                    ents.add(m.group(1))
                m = re.match(r"\s*(\S+)\s+[|}o.\-{]+\s+(\S+)\s*:", line)
                if m:
                    ents.update(m.groups())
    if ents:
        names = {o["title"].removesuffix("テーブル"): o for o in objs}
        out += [f"- 差異：ER 図の「{e}」に対応する開発オブジェクトがない" for e in sorted(ents) if e not in names]
        out += [f"- 差異：{label(o)} が ER 図にない" for n, o in names.items() if n not in ents]
        return out or ["- 差異なし（ER 図のエンティティと開発オブジェクトが一致）"]
    ops = set()
    for lang, code in blocks:
        if lang == "yaml" and "openapi" in code:
            for path, methods in (yaml.safe_load(code).get("paths") or {}).items():
                ops |= {f"{m.upper()} {path}" for m in methods}
    if ops:
        have = {o.get("operation"): o for o in objs}
        out += [f"- 差異：OpenAPI の「{op}」に対応する開発オブジェクトがない" for op in sorted(ops) if op not in have]
        out += [f"- 差異：{label(o)} が OpenAPI にない" for op, o in have.items() if op not in ops]
        return out or ["- 差異なし（OpenAPI のオペレーションと開発オブジェクトが一致）"]
    return ["- 自動突合の対象外（形式：" + str(c.get("format")) + "）。契約内容と開発オブジェクトを目視で確認する"]


def render_contract(nodes, cid):
    c = by_id(nodes)[cid]
    func = c["type"] == "機能契約"
    v = c.get("verified") or {}
    L = [f"# 契約書　{label(c)}", ""]
    rows = [("契約ID", cid), ("契約名", c["title"]), ("種別", c["type"]), ("版", c.get("revision")), ("状態", STATUS_JA.get(c.get("status"), c.get("status")))]
    if func:
        prov = nodes[c["provider"]]
        sysn = system_of(nodes, prov["_path"])
        rows += [("提供", f"{label(sysn)} / {label(prov)}"),
                 ("形式", c.get("format")), ("厚さ", c.get("thickness")), ("参照資料", c.get("resource"))]
    else:
        rows += [("品質特性", c.get("quality")), ("目標", c.get("target")), ("目標値", c.get("target_amount")), ("単位", c.get("unit"))]
    rows += [("作成日", date.today().isoformat()), ("生成元", "OKF バンドル（（導出）の節は取り込み時に無視される）")]
    L += attr_table(rows)
    L += ["", "## 1. 契約内容", "", body_rest(c) or MISSING, ""]
    n = 2
    if not func:
        L += [f"## {n}. 配分", "", "| 配分先 | 配分 | 数値 | 合成 | 内包先 |", "|---|---|---|---|---|"]
        L += [f"| {short_target(nodes, a)} | {a['value']} | {a.get('amount', '―')} | {a.get('role', '―')} | "
              f"{label(nodes[a['within']]) if a.get('within') else '―'} |" for a in c.get("allocations") or []]
        L += [""]
        n += 1
    else:
        L += [f"## {n}. 提供コンポーネントの開発オブジェクト（導出）", ""]
        L += [f"- {label(o)}（{o['kind']}）" for o in children(nodes, c["provider"])] or ["なし"]
        L += ["", f"## {n + 1}. 突合結果（導出）", ""] + reconcile(nodes, c) + [""]
        n += 2
    L += [f"## {n}. 利用者（導出）", "", "| 開発オブジェクト | システム | 参照先 | CRUD | 前提版 | 状態 |", "|---|---|---|---|---|---|"]
    for o in by_type(nodes, "開発オブジェクト"):
        for u in o.get("uses") or []:
            if u["contract"] == c["_path"]:
                st = "要確認" if u.get("rev", 0) < c.get("revision", 1) else "最新"
                L.append(f"| {label(o)} | {system_of(nodes, o['_path'])['title']} | {short_target(nodes, u)} | {u.get('crud') or '―'} | {u.get('rev')} | {st} |")
    L += ["", f"## {n + 1}. 参照する要件（導出）", "", "| 要件 | 参照先 | 前提版 | 状態 |", "|---|---|---|---|"]
    for s in by_type(nodes, "要件"):
        for r in s.get("contracts") or []:
            if r["contract"] == c["_path"]:
                st = "要確認" if r.get("rev", 0) < c.get("revision", 1) else "最新"
                L.append(f"| {label(s)} | {short_target(nodes, r)} | {r.get('rev')} | {st} |")
    at = scalar(v["at"]) if v.get("at") else ""
    L += ["", f"## {n + 2}. レビュー", "", "| 確認者 | 確認日時 |", "|---|---|", f"| {v.get('by', '')} | {at} |", "",
          "確認観点：", "",
          "- 突合結果に差異がないか。契約に主従はないため、差異は当事者間の衝突として裁定で解決する",
          "- 利用者の参照先・CRUD が契約内容と矛盾しないか",
          "- 要確認の参照が解消されているか",
          "", "確認後、確認者と確認日時を記入して取り込むと OKF の verified に反映される。"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    nodes, _ = load(Path(sys.argv[1]))
    cmd, target = sys.argv[2], sys.argv[3]
    print({"spec": render_spec, "design": render_design, "contract": render_contract}[cmd](nodes, target), end="")
