"""OKF バンドルの試作チェッカー（メタモデル検証用）。

使い方:
  python tools/okf_check.py <bundle>               整合性チェック
  python tools/okf_check.py <bundle> impact <id>   開発オブジェクトまたは契約を変更したときの直接の影響

版：各概念は revision を持ち、参照（from / contracts / uses）は前提にした上流の版を rev に持つ。
上流の revision が rev より新しい参照は「要確認（古い版が前提）」として報告する。
"""
import sys
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
DATA_KINDS = {"テーブル", "ファイル"}


def load(bundle: Path):
    nodes, errors = {}, []
    for p in sorted(bundle.rglob("*.md")):
        if p.name in RESERVED:
            continue
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            errors.append(f"{p}: フロントマターがない")
            continue
        _, fm, body = text.split("---", 2)
        fm = yaml.safe_load(fm) or {}
        if not fm.get("type"):
            errors.append(f"{p}: type がない")
        path = "/" + p.relative_to(bundle).as_posix()
        # from は { ref, rev } の配列。扱いやすいようにパスの配列も持つ
        fm["_from"] = [f for f in fm.get("from") or [] if isinstance(f, dict)]
        fm["from"] = [f["ref"] if isinstance(f, dict) else f for f in fm.get("from") or []]
        nodes[path] = {**fm, "_path": path, "_body": body}
    return nodes, errors


def contract_refs(n):
    """要件の contracts と開発オブジェクトの uses を共通の形で返す。"""
    return (n.get("contracts") or []) + (n.get("uses") or [])


def targets(ref):
    """契約参照が指す先（コンポーネント 1 つ、または開発オブジェクトの配列）。"""
    return [ref["component"]] if ref.get("component") else list(ref.get("objects") or [])


def refs(n):
    """ノードが持つ参照を (関係名, 参照先) で列挙する。"""
    for r in n.get("from") or []:
        yield "from", r
    for f in ("parent", "provider"):
        if n.get(f):
            yield f, n[f]
    for ref in contract_refs(n):
        yield "contract", ref["contract"]
        for t in targets(ref):
            yield "target", t
    for a in n.get("allocations") or []:
        for x in targets(a):
            yield "allocation", x
    for u in n.get("usecase") or []:
        if u.get("screen"):
            yield "usecase", u["screen"]


def by_type(nodes, t):
    return [n for n in nodes.values() if n.get("type") == t]


def check(nodes):
    errs = []
    for n in nodes.values():
        for rel, r in refs(n):
            if r not in nodes:
                errs.append(f"{n['id']}: {rel} の参照先がない {r}")
        if "revision" not in n:
            errs.append(f"{n.get('id', n['_path'])}: revision がない")
    # 契約参照の形
    for n in by_type(nodes, "要件") + by_type(nodes, "開発オブジェクト"):
        for ref in contract_refs(n):
            c = nodes.get(ref["contract"], {})
            has_c, has_o = bool(ref.get("component")), bool(ref.get("objects"))
            if c.get("type") == "非機能契約":
                if has_c or has_o:
                    errs.append(f"{n['id']}: 非機能契約 {c['id']} に参照先を書いている")
                continue
            if has_c == has_o:
                errs.append(f"{n['id']}: {c.get('id')} は component か objects のどちらか一方を書く")
            if has_c and ref["component"] != c.get("provider"):
                errs.append(f"{n['id']}: {c.get('id')} の component が提供コンポーネントと異なる")
            for o in ref.get("objects") or []:
                if nodes.get(o, {}).get("parent") != c.get("provider"):
                    errs.append(f"{n['id']}: {o} は {c.get('id')} の提供コンポーネント配下にない")
            if ref.get("crud") and not set(ref["crud"]) <= set("CRUD"):
                errs.append(f"{n['id']}: crud の値が不正 {ref['crud']}")
    # 非機能契約の配分先も component か objects のどちらか一方
    for c in by_type(nodes, "非機能契約"):
        for a in c.get("allocations") or []:
            if bool(a.get("component")) == bool(a.get("objects")):
                errs.append(f"{c['id']}: 配分先は component か objects のどちらか一方を書く")
    # ユースケースは補足情報。画面を参照する（契約の経路には数えない）
    for n in by_type(nodes, "要求") + by_type(nodes, "要件"):
        for u in n.get("usecase") or []:
            s = nodes.get(u.get("screen"), {})
            if s and s.get("kind") != "画面":
                errs.append(f"警告 {n['id']}: ユースケースが画面以外を参照している {s['id']}")
    # 要件の種別と契約の種別
    for s in by_type(nodes, "要件"):
        if not s.get("contracts"):
            errs.append(f"{s['id']}: 要件が契約に紐づいていない")
        want = "機能契約" if s.get("category") == "機能" else "非機能契約"
        for ref in s.get("contracts") or []:
            ct = nodes.get(ref["contract"], {}).get("type")
            if ct and ct != want:
                errs.append(f"{s['id']}: {s.get('category')}要件が {ct} を指している")
    for c in by_type(nodes, "機能契約"):
        if not c.get("provider"):
            errs.append(f"{c['id']}: 提供コンポーネントがない")
        if not any(r["contract"] == c["_path"] for o in by_type(nodes, "開発オブジェクト") for r in o.get("uses") or []):
            errs.append(f"{c['id']}: 利用する開発オブジェクトがない")
    # 上流で下流から参照されないもの
    referenced = {r for n in nodes.values() for _, r in refs(n)}
    for t in ("要望", "要求"):
        for n in by_type(nodes, t):
            if n["_path"] not in referenced:
                errs.append(f"{n['id']}: 下流から参照されていない（{t}）")
    # 書き込む開発オブジェクトがないデータ
    for d in by_type(nodes, "開発オブジェクト"):
        if d.get("kind") not in DATA_KINDS:
            continue
        crud = crud_of(nodes, d["_path"])
        if not any(set(v) & set("CU") for v in crud.values()):
            errs.append(f"警告 {d['id']} {d['title']}: 登録・更新する開発オブジェクトがない（要件の抜けの可能性）")
    return errs


def versioned_refs(n):
    """版を持つべき参照を (上流パス, rev) で列挙する。"""
    for f in n.get("_from") or []:
        yield f["ref"], f.get("rev")
    for ref in contract_refs(n):
        yield ref["contract"], ref.get("rev")


def stale(nodes):
    out = []
    for n in nodes.values():
        for up, rev in versioned_refs(n):
            u = nodes.get(up)
            if not u:
                continue
            if rev is None:
                out.append(f"{n['id']}: {u['id']} への参照に rev がない")
            elif u.get("revision", 1) > rev:
                out.append(f"要確認 {n['id']}: {u['id']} は r{u.get('revision')} だが r{rev} を前提にしている")
    return out


def crud_of(nodes, data_path):
    """データ（テーブル・ファイル）に対する開発オブジェクトごとの CRUD。"""
    out = {}
    for o in by_type(nodes, "開発オブジェクト"):
        for ref in o.get("uses") or []:
            if data_path in (ref.get("objects") or []) and ref.get("crud"):
                out[o["_path"]] = "".join(sorted(set(out.get(o["_path"], "") + ref["crud"]), key="CRUD".index))
    return out


def allocated_to(alloc, obj):
    """配分が開発オブジェクトに及ぶか（コンポーネント全体、または名指し）。"""
    return alloc.get("component") == obj["parent"] or obj["_path"] in (alloc.get("objects") or [])


def reverse(nodes):
    rev = {}
    for n in nodes.values():
        for rel, r in refs(n):
            rev.setdefault(r, []).append((rel, n["_path"]))
    return rev


def referrers(nodes, contract_path, obj_path=None):
    """契約を参照する要件・開発オブジェクト。obj_path を渡すと、その開発オブジェクトを含む参照に限る。"""
    out = []
    for n in by_type(nodes, "要件") + by_type(nodes, "開発オブジェクト"):
        for ref in contract_refs(n):
            if ref["contract"] != contract_path:
                continue
            if obj_path is None or ref.get("component") or obj_path in (ref.get("objects") or []):
                out.append(n["_path"])
    return list(dict.fromkeys(out))


def impact(nodes, start_id):
    """開発オブジェクトまたは契約の変更が直接波及する範囲。

    契約を影響の防波堤とみなし、利用側の開発オブジェクトで止める。
    利用側の変更がさらに利用側の提供する契約を変えるかは人が判断し、改めて impact を実行する。
    """
    rev = reverse(nodes)
    start = next(n for n in nodes.values() if n.get("id") == start_id)
    if start["type"] == "開発オブジェクト":
        comp = start["parent"]
        contracts = [p for rel, p in rev.get(comp, []) if rel == "provider"]
        nonfunc = [c["_path"] for c in by_type(nodes, "非機能契約")
                   if any(allocated_to(a, start) for a in c.get("allocations") or [])]
        hits = [p for c in contracts for p in referrers(nodes, c, start["_path"])]
        hits += [p for c in nonfunc for p in referrers(nodes, c)]
        out = [("契約", p) for p in contracts + nonfunc]
    else:
        hits = referrers(nodes, start["_path"])
        out = []
    for p in dict.fromkeys(hits):
        out.append(("要確認" if nodes[p]["type"] == "開発オブジェクト" else "関連要件", p))
    return [(k, nodes[p]) for k, p in out]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    bundle = Path(sys.argv[1])
    nodes, errors = load(bundle)
    if len(sys.argv) == 2:
        errors += check(nodes) + stale(nodes)
        print(f"{len(nodes)} concepts")
        print("\n".join(errors) if errors else "OK")
    elif sys.argv[2] == "impact":
        for kind, n in impact(nodes, sys.argv[3]):
            print(f"{kind:<6} {n['id']:<12} {n['title']}")
