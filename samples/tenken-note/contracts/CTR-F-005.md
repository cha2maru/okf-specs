---
type: 機能契約
id: CTR-F-005
revision: 1
title: メール送信
provider: /structure/CMP-0501.md
format: 外部API仕様
thickness: 厚い
resource: https://example.com/mail-service/api-docs
status: draft
---

# CTR-F-005：メール送信（クラウドバックエンド ⇔ 外部メール配信サービス）

提供者が外部のため、契約の内容は先方の公開仕様への参照と、利用する範囲の取り決めのみ。

- 利用 API：`POST /v1/send`
- 送信元アドレス：`no-reply@tenken.example`
- 送信上限：100 通/秒（先方プランによる）
