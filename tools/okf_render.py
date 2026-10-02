"""OKF バンドルから人・SDD ツール向けの文書を生成する（試作）。

OKF は AI が間違えないための正本。ここで生成する文書は出力物であり、手で編集しない。

使い方:
  python tools/okf_render.py <bundle> spec <REQ-id>     SDD Spec（spec-kit の spec.md 相当）
  python tools/okf_render.py <bundle> design <SYS-id>   機能設計書（システム単位）
"""
import re
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from okf_check import DATA_KINDS, allocated_to, by_type, contract_refs, crud_of, load, targets  # noqa: E402

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


def interface_of(nodes, obj, missing):
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
                if op:
                    dumped = yaml.safe_dump({obj["operation"]: op}, allow_unicode=True, sort_keys=False)
                    return f"出典：{label(c)}\n\n```yaml\n{dumped}```"
    if obj.get("kind") == "画面":
        items = section(obj["_body"], "画面項目")
        if items:
            return "**画面項目**\n\n" + items
    for c in provided:
        blocks = code_blocks(c["_body"])
        if blocks:
            return f"受信するメッセージ（出典：{label(c)}）\n\n" + "\n".join(f"```{l}\n{b}```" for l, b in blocks)
    missing.append(f"{obj['id']} インターフェース")
    return MISSING


def render_design(nodes, sys_id):
    ids = by_id(nodes)
    system = ids[sys_id]
    product = nodes[system["parent"]]
    comps = children(nodes, system["_path"])
    objs = [o for c in comps for o in children(nodes, c["_path"])]
    funcs = [o for o in objs if o.get("kind") not in DATA_KINDS]
    missing = []

    L = [
        f"# 機能設計書　{system['title']}",
        "",
        "| 項目 | 内容 |",
        "|---|---|",
        f"| プロダクト | {product['title']}（{product['id']}） |",
        f"| システム | {system['title']}（{sys_id}） |",
        f"| 作成日 | {date.today().isoformat()} |",
        "| 生成元 | OKF バンドル（本書は生成物。修正は OKF 側で行う） |",
        "",
        "## 改版履歴",
        "",
        "| 版 | 日付 | 内容 |",
        "|---|---|---|",
        f"| 0.1 | {date.today().isoformat()} | 初版（生成） |",
        "",
        "## 1. システム概要",
        "",
        system["_body"].split("\n", 3)[-1].strip() or MISSING,
        "",
        "## 2. 構成",
        "",
        "| コンポーネント | 種別 | 開発オブジェクト |",
        "|---|---|---|",
    ]
    for c in comps:
        L.append(f"| {label(c)} | {c['kind']} | {'<br>'.join(label(o) for o in children(nodes, c['_path'])) or '―'} |")

    L += ["", "## 3. 機能一覧", "", "| 機能ID | 機能名 | 種別 | コンポーネント | 関連要求・要件 |", "|---|---|---|---|---|"]
    for o in funcs:
        rs = ", ".join(s["id"] for s, _ in related_specs(nodes, o)) or "―"
        L.append(f"| {o['id']} | {o['title']} | {o['kind']} | {nodes[o['parent']]['title']} | {rs} |")

    L += ["", "## 4. 機能詳細"]
    for i, o in enumerate(funcs, 1):
        comp = nodes[o["parent"]]
        L += ["", f"### 4.{i} {o['title']}（{o['id']}）", ""]
        L += [f"#### 4.{i}.1 概要", "", section(o["_body"], "概要") or (missing.append(f"{o['id']} 概要") or MISSING), ""]
        L += [f"#### 4.{i}.2 関連要求・要件", ""]
        rs = related_specs(nodes, o)
        L += [f"- {label(s)}（{s.get('category', s['type'])}・{how}）" for s, how in rs] or [MISSING]
        L += ["", f"#### 4.{i}.3 インターフェース", "", interface_of(nodes, o, missing), ""]
        iac = o.get("kind") == "IaCリソース"
        heading, sec = ("設定内容", "設定") if iac else ("処理内容", "処理")
        L += [f"#### 4.{i}.4 {heading}", "", section(o["_body"], sec) or (missing.append(f"{o['id']} {sec}") or MISSING), ""]
        L += [f"#### 4.{i}.5 使用データ", ""]
        data = [(u, t) for u in o.get("uses") or [] for t in targets(u) if is_data(nodes, t)]
        if data:
            L += ["| データ | 契約 | CRUD |", "|---|---|---|"]
            L += [f"| {label(nodes[t])} | {nodes[u['contract']]['id']} | {u.get('crud') or MISSING} |" for u, t in data]
        else:
            L += ["なし"]
        calls = [u for u in o.get("uses") or [] if not all(is_data(nodes, t) for t in targets(u))]
        L += ["", f"#### 4.{i}.6 利用する契約（データ以外）", ""]
        L += [f"- {label(nodes[u['contract']])} → {ref_target_label(nodes, u)}" for u in calls] or ["なし"]
        err = section(o["_body"], "エラー") or ("―（IaC リソース）" if iac else (missing.append(f"{o['id']} エラー処理") or MISSING))
        L += ["", f"#### 4.{i}.7 エラー処理", "", err, ""]
        nf = [(c, a) for c in by_type(nodes, "非機能契約") for a in c.get("allocations") or [] if allocated_to(a, o)]
        L += [f"#### 4.{i}.8 非機能要件（配分）", ""]
        L += [f"- {label(c)}：{a['value']}" for c, a in nf] or ["なし"]

    # CRUD 図
    data_paths = list(dict.fromkeys(t for o in funcs for u in o.get("uses") or [] for t in targets(u) if is_data(nodes, t)))
    L += ["", "## 5. CRUD 図", ""]
    if data_paths:
        L += ["| 機能 ＼ データ | " + " | ".join(nodes[d]["title"] for d in data_paths) + " |",
              "|---|" + "---|" * len(data_paths)]
        for o in funcs:
            row = [crud_of(nodes, d).get(o["_path"], "") for d in data_paths]
            if any(row):
                L.append(f"| {o['title']} | " + " | ".join(row) + " |")
    for d in writers_missing(nodes, [o["_path"] for o in objs if o.get("kind") in DATA_KINDS]):
        missing.append(f"{nodes[d]['id']} {nodes[d]['title']} を登録・更新する機能がない")

    # 外部インターフェース
    L += ["", "## 6. 外部インターフェース", "", "| 方向 | 契約 | 相手システム | 参照先 |", "|---|---|---|---|"]
    comp_paths = {c["_path"] for c in comps}
    for o in by_type(nodes, "開発オブジェクト"):
        for u in o.get("uses") or []:
            c = nodes[u["contract"]]
            mine_provides = c.get("provider") in comp_paths
            mine_uses = o["parent"] in comp_paths
            if mine_provides and not mine_uses:
                L.append(f"| 提供 | {label(c)} | {system_of(nodes, o['_path'])['title']}（{o['title']}） | {ref_target_label(nodes, u)} |")
            elif mine_uses and not mine_provides:
                L.append(f"| 利用 | {label(c)} | {system_of(nodes, c['provider'])['title']} | {ref_target_label(nodes, u)} |")

    # 非機能
    L += ["", "## 7. 非機能要件", "", "| 非機能契約 | 全体目標 | 配分先 | 配分 |", "|---|---|---|---|"]
    obj_paths = {o["_path"] for o in objs}
    for c in by_type(nodes, "非機能契約"):
        for a in c.get("allocations") or []:
            if a.get("component") in comp_paths or set(a.get("objects") or []) & obj_paths:
                L.append(f"| {label(c)} | {c['target']} | {ref_target_label(nodes, a)} | {a['value']} |")

    L += ["", "## 8. 未記載・確認事項", ""]
    L += [f"- {m}" for m in missing] or ["なし"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    nodes, _ = load(Path(sys.argv[1]))
    cmd, target = sys.argv[2], sys.argv[3]
    print({"spec": render_spec, "design": render_design}[cmd](nodes, target), end="")
