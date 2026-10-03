---
type: 機能契約
id: CTR-F-007
revision: 1
title: 異常イベント
provider: /structure/CMP-0203.md
format: メッセージ定義
thickness: 薄い
elements: [異常イベント]
status: draft
---

# CTR-F-007：異常イベント

異常通知コンポーネントが「受け付けるメッセージ」として提供する。点検 API が発行側として利用する。

```json
{ "inspectionId": "string", "siteId": "string", "equipmentId": "string", "anomalyItems": ["code"] }
```

注：イベントの「提供者」を発行側にするか購読側にするかは、モデル上まだ決まっていない（サンプルで発見した論点）。
