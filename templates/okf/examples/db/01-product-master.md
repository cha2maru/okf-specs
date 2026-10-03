---
type: 開発オブジェクト
id: OBJ-140201
revision: 1
title: 商品テーブル
kind: テーブル
entities: [商品]
parent: /structure/CMP-1402.md
status: draft
tags: [商品, マスタ]
# 提供する契約：商品DB（/contracts/CTR-F-104.md）のエンティティ「商品」。契約側の elements と突合する。
# 読み書きする側（商品管理API が CRUD、在庫検索API が R など）は、利用する側の uses に書く。
---

# OBJ-140201：商品テーブル

> 例：RDB のマスタテーブルの書き方。コード値の定義、論理削除、履歴を持たないことを明記し、共通項目はシステムの共通方針に任せて差分だけを書く（題材：商品マスタテーブル）

## 概要

1 行＝1 商品（SKU 単位）。商品コードは業務で使う不変のキーで、名称・価格・カテゴリは上書きで更新する。

- **履歴は持たない**。価格の変更履歴が必要な場合は、受注明細側に受注時点の単価を持たせる（受注DB の契約で取り決め済み）。
- 変更の監査はシステム共通の監査ログで行い、このテーブルには持たない。

## 項目定義

共通項目（created_at、created_by、updated_at、updated_by）はシステムの共通方針どおりのため省略する。

| 論理名 | 物理名 | 型 | 桁 | 必須 | キー | 既定値 | 説明 |
|---|---|---|---|---|---|---|---|
| 商品 ID | product_id | bigint | | ○ | PK | 採番（identity） | 内部キー。画面には出さない |
| 商品コード | product_code | varchar | 10 | ○ | UK | | 半角英数大文字。登録後は変更不可 |
| 商品名 | product_name | varchar | 100 | ○ | | | |
| 商品名カナ | product_name_kana | varchar | 200 | ○ | | | 全角カナ。並び替え・検索用 |
| カテゴリコード | category_code | char | 2 | ○ | FK | | カテゴリテーブルを参照 |
| 単位コード | unit_code | char | 2 | ○ | | '01' | コード値を参照 |
| 標準単価 | standard_price | numeric | 10,2 | ○ | | 0 | 税抜、円 |
| 税区分 | tax_type | char | 1 | ○ | | '1' | コード値を参照 |
| 発注点 | reorder_point | integer | | ○ | | 0 | 在庫がこれを下回ると「少ない」 |
| 販売状態 | sales_status | char | 1 | ○ | | '1' | コード値を参照 |
| 削除フラグ | deleted | boolean | | ○ | | false | 論理削除 |
| 削除日時 | deleted_at | timestamptz | | | | | 論理削除した日時 |

## インデックス・制約

| 名前 | 項目 | 種類 | 目的 |
|---|---|---|---|
| pk_product | product_id | 主キー | |
| uk_product_code | product_code | 一意 | 論理削除した行も含めて一意（コードの再利用を禁止） |
| fk_product_category | category_code → category.category_code | 外部キー | |
| ix_product_kana | product_name_kana | 通常 | 一覧の並び替え |
| ix_product_category | category_code, deleted | 通常 | カテゴリでの絞り込み |
| ck_product_price | standard_price >= 0 | チェック | |

## 状態値・コード値

コード値はコードテーブルではなく、ここに定義してアプリの列挙型と一致させる（値が増えることはまれで、増えるときは改版する）。

| 項目 | 値 | 意味 |
|---|---|---|
| unit_code | 01 | 個 |
| | 02 | 箱 |
| | 03 | kg |
| tax_type | 1 | 標準税率 |
| | 2 | 軽減税率 |
| | 9 | 非課税 |
| sales_status | 1 | 販売中 |
| | 2 | 販売停止（受注不可、在庫・照会は可） |
| | 3 | 廃番（新規の入庫も不可） |

## 論理削除

- 削除は deleted=true、deleted_at を設定する。物理削除はしない（受注・在庫の明細から参照されるため）。
- 通常の検索は deleted=false の行だけを対象にする。削除済みを含めるのは商品管理画面の「削除済みも表示」だけ。
- 削除の取り消しは deleted=false に戻す。商品コードは一意のままなので衝突しない。
- 販売状態「廃番」と論理削除の違い：廃番は業務上の状態で照会に出る。論理削除は誤登録の取り消しで、照会にも出さない。

## 件数見込み

| 初期 | 月次増分 | 累積（保持期間内） |
|---|---|---|
| 12,000 件（旧システムから移行） | 100 件 | 約 20,000 件（7 年後） |

## 保持・削除

- 保持期間：無期限（マスタのため）。
- 論理削除した行も物理削除しない。
