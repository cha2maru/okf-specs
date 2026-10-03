---
type: Concept Definition
title: 要望
description: 「〇〇したい」で表される、プロダクトに対する願望
status: draft
tags: [metamodel, requirements]
---

# 要望

## 定義

プロダクトに対する願望。「**〇〇したい**」で表現される。実現するかどうかは未確定。

## 性質

- [裁定](/concepts/ruling.md) の結果として生まれる。
- レビューの結果、要望の時点で落とされる（要求に進まない）ことがある。採否の判断はレビューの範疇とする。
- 採否は `disposition`（未整理／採用／統合／保留／却下）に書く。採用なのに要求につながっていない要望、却下・保留なのにつながっている要望はチェッカーが警告する。

## リレーション

- 裁定 → 要望：1対多
- 要望 ⇔ [要求](/concepts/requirement.md)：**多対多**
