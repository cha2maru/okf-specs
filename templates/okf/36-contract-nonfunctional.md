---
type: 非機能契約
id: CTR-N-000               # 必須
revision: 1                 # 必須
title: ＜品質の名前＞          # 必須
quality: 性能効率性           # 必須。品質特性（分類体系は未決 #9）
target: ＜主目標の数値と計測区間＞  # 必須。主目標を 1 つだけ。p99 など副目標は本文に
unit: 秒                     # 数値で表せる目標のとき。target_amount・amount の単位
target_amount: 3.0          # 数値で表せる目標のとき。加算の amount の合計がこれを超えないことをチェックする
allocations:                # 必須。component（全体）か objects（一部）のどちらか
  - { component: /structure/CMP-0000.md, value: ＜配分の説明＞, amount: 1.0, role: 加算 }
  - { objects: [/structure/OBJ-000000.md], value: ＜配分の説明＞, amount: 0.5, role: 内包, within: /structure/CMP-0000.md }
  - { component: /structure/CMP-0000.md, value: ＜配分の説明＞, role: 条件 }
status: draft
tags: []
# role：加算＝目標に足し込む／内包＝within の配分の内側（足さない。within の amount を超えない）／条件＝時間を持たない前提（amount なし）
---

# CTR-N-000：＜品質の名前＞

## 目標

<!-- 数値、計測区間（起点と終点）、p95 か平均か。副目標。 -->

## 計測条件

<!-- 同時利用者数、データ量、端末、回線。 -->

## 配分

<!-- フロントマターの配分を、合成の仕方つきで説明する。配分のない区間・余裕も書く（未配分の区間を残さない）。 -->

| 区間・配分先 | 配分値 | 合成 | 備考 |
|---|---|---|---|
| ＜配分先＞ | | 加算 | |
| ＜内側の配分先＞ | | 内包（上の行に含まれる） | |
| ＜ネットワーク等＞ | | 配分先なし（計測条件で固定） | |
| 余裕 | | | |

## 測定・検証方法

| 配分先 | 手段 | タイミング | 検証環境 |
|---|---|---|---|

## 未達時の扱い
