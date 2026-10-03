---
type: 機能契約
id: CTR-F-002
revision: 1
title: 注文確定イベント
provider: /structure/CMP-0103.md
format: メッセージ定義
thickness: 厚い
elements: [OrderConfirmed]
status: draft
tags: [注文, イベント, 非同期]
---

> 例：システムをまたぐイベントを厚い契約として書き、配送保証・重複・DLQ を利用側が実装できる粒度で決める（題材：注文確定イベント）

# CTR-F-002：注文確定イベント

<!-- provider は受け付ける側（在庫引当）。発行側を provider にするかは未決（#20）。 -->

## 当事者

| 役割 | コンポーネント | 開発オブジェクト |
|---|---|---|
| 発行 | CMP-0102 注文API（SYS-01） | OBJ-010201 注文登録API（決済承認の後に発行） |
| 購読（提供側） | CMP-0103 在庫引当（SYS-01） | OBJ-010301 在庫引当処理 |
| 購読 | CMP-0601 出荷連携（SYS-06 物流連携） | OBJ-060101 出荷指示作成処理 |

## 配送

| 項目 | 内容 |
|---|---|
| 伝達基盤 | トピック `chumon-order-confirmed`（OBJ-020501）から購読者ごとのキューへ配る |
| 宛先 | 在庫引当：`zaiko-hikiate-q`（OBJ-020502）、出荷連携：`shukka-renkei-q`（OBJ-020503） |
| 配送保証 | at-least-once（同じイベントが 2 回以上届くことがある） |
| 順序 | 保証しない。同じ注文のイベントは 1 回しか発行しない（注文の確定は 1 回）ため、順序に依存しない |
| 重複時の扱い | 購読側は `eventId` で重複を除く。処理済みの `eventId` を 7 日間保持する |
| 発行の確実さ | 発行側は注文の確定と同じトランザクションで送信待ちテーブルに書き、別プロセスが送る（トランザクショナルアウトボックス） |
| メッセージの上限 | 256 KB。明細は 200 行まで（注文の上限と同じ。CTR-F-001 参照） |

## 項目

| 項目 | 型 | 必須 | 説明 |
|---|---|---|---|
| eventId | string(uuid) | ○ | 重複排除のキー。再送しても変わらない |
| eventType | string | ○ | 固定値 `OrderConfirmed` |
| occurredAt | string(date-time) | ○ | 注文が確定した日時（送信日時ではない）。`+09:00` 付き |
| schemaVersion | integer | ○ | 現在 1 |
| orderId | string | ○ | `O` ＋ 12 桁 |
| customerId | string | ○ | 会員 ID。個人情報（氏名・住所）は載せない。必要なら購読側が会員 API で引く |
| warehouseId | string | ○ | 出荷元の倉庫 |
| items | array | ○ | 1〜200 件 |
| items[].sku | string | ○ | 商品コード |
| items[].quantity | integer | ○ | 1 以上 |
| totalAmount | integer | ○ | 税込合計（円） |
| deliveryDate | string(date) | | 指定がなければ省略 |

```json
{
  "eventId": "7f1c2e9a-3b4d-4c6e-9a10-2b3c4d5e6f70",
  "eventType": "OrderConfirmed",
  "occurredAt": "2026-10-03T14:05:12+09:00",
  "schemaVersion": 1,
  "orderId": "O202610030001",
  "customerId": "C00012345",
  "warehouseId": "W01",
  "items": [{ "sku": "4901234567894", "quantity": 2 }],
  "totalAmount": 5280
}
```

## 失敗時の扱い

| 事象 | 扱い |
|---|---|
| 購読側の処理失敗（一時的） | 受信を確定しない。可視性タイムアウト 60 秒後に再配送 |
| 再配送の上限 | 5 回。超えたら購読者ごとの DLQ（`zaiko-hikiate-dlq`：OBJ-020504、`shukka-renkei-dlq`：OBJ-020505）へ移す |
| DLQ の保持 | 14 日 |
| DLQ の監視 | 1 件でも入ったら購読側の担当へ通知 |
| DLQ からの再処理 | 原因を直した後、運用手順 OPS-031 で元のキューへ戻す。`eventId` で重複を除くため再投入してよい |
| 項目の不正（スキーマ違反） | 再試行しても直らないため、受信を確定せず即 DLQ へ（再配送を待たない） |
| 発行側の送信失敗 | 送信待ちテーブルに残し、30 秒ごとに再送。1 時間送れなければ注文アプリ担当へ通知 |

## 互換性

- 項目の追加（任意項目）は互換とみなし、`schemaVersion` は上げない。購読側は知らない項目を無視する。
- 項目の削除・改名・型変更・必須化は破壊的変更。`schemaVersion` を上げ、新旧両方を 3 か月並行して発行する（購読側は `schemaVersion` で読み分ける）。
- 購読者の追加は、この契約の改版ではなく当事者表の更新とする。
