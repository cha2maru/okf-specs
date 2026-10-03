---
type: 要求
id: REQ-000                 # 必須
revision: 1                 # 必須
title: ＜（利用者が）〇〇ができる＞  # 必須。主語は原則として利用者・業務
status: draft               # 必須
actor: ＜点検者＞             # 必須。主語のアクター（検索・権限の突合に使う）。プロダクトのアクター一覧にある名前
priority: must              # 任意。must／should／could／wont（検索用）
from:                       # 必須。由来する要望（多対多）
  - { ref: /wishes/WSH-000.md, rev: 1 }
usecase:                    # 任意（補足）。画面は参照するだけで契約ではない
  - { step: ＜手順＞, screen: /structure/OBJ-000000.md }
tags: []
---

# REQ-000：＜〇〇ができる＞

## 背景・目的

<!-- 要望から何を実現すると決めたか。 -->

## ユースケース

<!-- フロントマターの usecase を、前提・例外も含めて文章で補う。 -->

## 対象外

<!-- この要求に含めないこと。 -->
