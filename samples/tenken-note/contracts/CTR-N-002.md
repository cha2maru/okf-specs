---
type: 非機能契約
id: CTR-N-002
revision: 1
title: 異常通知の即時性
quality: 性能効率性
target: 点検結果受信から送信 API 受付まで 5 分以内
unit: 秒
target_amount: 300
allocations:
  - { objects: [/structure/OBJ-020101.md], value: 受信から異常イベント発行まで 10 秒以内, amount: 10, role: 加算 }
  - { component: /structure/CMP-0203.md, value: イベント受信から送信 API 呼び出しまで 1 分以内（リトライ込み）, amount: 60, role: 加算 }
  - { component: /structure/CMP-0501.md, value: 先方 SLA に依存（自分たちでは制御できない）, role: 条件 }
status: draft
---

# CTR-N-002：異常通知の即時性

外部コンポーネントへの配分は「約束」ではなく「前提」になる（サンプルで発見した論点）。
