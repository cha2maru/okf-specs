---
type: 非機能契約
id: CTR-N-003
revision: 1
title: クラウド可用性
quality: 可用性
target: 平日 8〜20 時の月間稼働率 99.5%
allocations:
  - { component: /structure/CMP-0404.md, value: 2 AZ に各 1 タスク以上、自動置き換え }
  - { component: /structure/CMP-0402.md, value: マルチ AZ・自動フェイルオーバー }
status: draft
---

# CTR-N-003：クラウド可用性

可用性は物理側（IaC）で実現するため、クラウド基盤のコンポーネントに配分する。
