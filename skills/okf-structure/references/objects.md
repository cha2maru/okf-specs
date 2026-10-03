# 開発オブジェクトの骨組み

この段階では、フロントマター（リレーション）と「概要」だけを書く。本文の他の節は okf-detail が書く。

## 種別ごとのフロントマター

| 種別 | テンプレート | 必ず書くもの |
|---|---|---|
| API | 20-object-api.md | `operation`（契約の `elements` と一致）、`uses` |
| 画面 | 21-object-screen.md | `roles`（プロダクトの actors）、`uses`、分かれば `transitions` |
| イベント処理 | 22-object-event.md | `uses`。受け付けるメッセージは親コンポーネントが提供する契約なので書かない |
| バッチ・バックグラウンド処理 | 23-object-batch.md | `uses` |
| テーブル | 24-object-table.md | `entities`（契約の `elements` と一致） |
| ファイル | 25-object-file.md | `entities` |
| IaC リソース | 26-object-iac.md | `depends_on`、実行環境なら `hosts` |
| オンライン処理 | 27-object-online.md | `uses` |

## サーバー側の開発オブジェクトを起こしたら

- 実行環境（コンテナサービスなどの IaC リソース）の `hosts` に足す。
- DB・ファイルを使うなら、論理の契約（ER 図・キー規約）に加えて、それを実現する接続情報の契約（`realizes` でたどれる）も `uses` に足す。
- チェッカーは、どちらの抜けも警告する。

## operation の書き方

`{}` を含むオペレーションは `"PUT /equipment/{equipmentId}/assignee"` のように引用符で囲む。

## uses の書き方

- 1 エントリ＝（契約, CRUD）の組。同じ契約でも CRUD が違えば分ける。
- データ（テーブル・ファイル）を使うなら `objects` に対象を並べ、`crud` を付ける。
- API を呼ぶなら `objects` に呼ぶ API を並べる。外部サービス・IaC の接続情報など契約全体なら `component`。
- 自分の親コンポーネントが提供する契約は書かない。
- `rev` は契約の現在の `revision`。
- 既存の開発オブジェクトに、改版した契約への参照を足すときは、既存の行は触らず、現在の `rev` の別の行で足す（古い行の `rev` は okf-change で上げる）。

## 名前だけで済ませない

本文や要件に名前だけ出てくるもの（設備マスタ、担当者、キュー、KMS キー、認証基盤など）は、開発オブジェクトとして起こす。起こさないと、契約の `elements` と突合できず、影響分析にも出てこない。
ただし、利用者が「未定」と答えたもの（認証の仕組みなど）は起こさず、関係するファイルに【要確認】を付けて報告する。

## 例

`templates/okf/examples/`（function、api、screen、db、iac）と、点検ノートのサンプル `samples/tenken-note/structure/`。
