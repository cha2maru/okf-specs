---
type: 非機能契約
id: CTR-N-004
revision: 1
title: 点検データ保護
quality: セキュリティ
target: 点検データを端末内・通信経路・クラウド上で暗号化する
allocations:
  - { component: /structure/CMP-0102.md, value: 端末内 DB の暗号化 }
  - { component: /structure/CMP-0401.md, value: TLS 1.2 以上のみ許可 }
  - { component: /structure/CMP-0402.md, value: 保存時暗号化（KMS） }
  - { component: /structure/CMP-0403.md, value: 保存時暗号化（KMS） }
status: draft
---

# CTR-N-004：点検データ保護
