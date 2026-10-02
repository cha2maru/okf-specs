---
type: Concept Definition
title: 要求
description: 「（利用者が）〇〇ができる」で表される、実現すると決めた利用者視点の能力
status: draft
tags: [metamodel, requirements]
---

# 要求

## 定義

実現すると決めた、利用者・業務から見た能力。「**〇〇ができる**」で表現する。

## 主語

主語は原則として**利用者・業務**とする。例外はありうる。

## 補足情報：ユースケース

要求（および要件）は、補足情報としてユースケースを持てる。画面はここで参照するだけで、**画面を契約とはみなさない**。

```yaml
usecase:
  - { step: 当月の点検対象設備を一覧から選ぶ, screen: /structure/OBJ-010101.md }
  - { step: 各点検項目を入力し、写真を撮って保存する, screen: /structure/OBJ-010102.md }
```

- ユースケースの参照は補足であり、「要件は必ず契約を経由する」の経路には数えない。
- Spec・機能設計書では、この参照から画面を対象に含める。

## リレーション

- [要望](/concepts/wish.md) ⇔ 要求：多対多
- 要求 ⇔ [要件](/concepts/specification.md)：**多対多**
