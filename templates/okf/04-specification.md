---
type: 要件
id: SPC-000                 # 必須
revision: 1                 # 必須
title: ＜（システムが）〇〇をする＞  # 必須。主語は原則としてシステム
category: 機能               # 必須。機能／非機能
status: draft               # 必須
priority: must              # 任意
from:                       # 必須。由来する要求（多対多）
  - { ref: /requirements/REQ-000.md, rev: 1 }
contracts:                  # 必須。機能要件→機能契約、非機能要件→非機能契約
  - { contract: /contracts/CTR-F-000.md, component: /structure/CMP-0000.md, rev: 1 }       # 契約全体
  - { contract: /contracts/CTR-F-000.md, objects: [/structure/OBJ-000000.md], rev: 1 }    # 一部
  - { contract: /contracts/CTR-N-000.md, rev: 1 }                                         # 非機能
acceptance:                 # 受入基準の ID（文章は任意。必須にするかは未決 #33）
  - { id: AC-000-1 }
tags: []
---

# SPC-000：＜〇〇をする＞

## 説明

<!-- 要求をどう実現するか。業務ルール・判断基準。 -->

## 受入基準

<!-- AC-ID ごとに 前提／操作／結果。非機能は測定条件と合格基準。 -->

- **AC-000-1**
  - **前提**
  - **操作**
  - **結果**
