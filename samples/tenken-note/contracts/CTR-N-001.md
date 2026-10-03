---
type: 非機能契約
id: CTR-N-001
revision: 1
title: ダッシュボード応答性能
quality: 性能効率性
target: 拠点進捗の表示 3 秒以内（p95）
unit: 秒
target_amount: 3.0
allocations:
  - { component: /structure/CMP-0301.md, value: 描画 1.0 秒以内, amount: 1.0, role: 加算 }
  - { component: /structure/CMP-0202.md, value: API 応答 1.5 秒以内, amount: 1.5, role: 加算 }
  - { objects: [/structure/OBJ-020401.md, /structure/OBJ-020402.md], value: 集計クエリ 0.5 秒以内, amount: 0.5, role: 内包, within: /structure/CMP-0202.md }
status: draft
---

# CTR-N-001：ダッシュボード応答性能

配分の合計（3.0 秒）が目標と一致していること。
