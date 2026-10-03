---
type: 機能契約
id: CTR-F-002
revision: 1
title: ローカルストア
provider: /structure/CMP-0102.md
format: 端末内スキーマ
thickness: 薄い
elements: [ローカル点検]
status: draft
---

# CTR-F-002：ローカルストア

同一システム内のため薄い契約。テーブル名と主要項目のみ。

| テーブル | 主要項目 |
|---|---|
| ローカル点検 | localId, equipmentId, items, photos(パス), sendState(未送信/送信済), idempotencyKey |
