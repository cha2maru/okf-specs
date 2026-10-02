# jtcsdd 設計ドキュメント

要望からウォーターフォールの設計までの概念・リレーションを、プロダクトに依存しない形で管理するための仕組み（メタモデル）の設計。
本ディレクトリは OKF (Open Knowledge Format) v0.2 のバンドルとして記述する。

## 全体像

- [メタモデル概要](/overview.md) — 概念の一覧と、要求側の流れ・構造側のツリーのつながり

## 概念

- [裁定](/concepts/ruling.md) — 発言と質疑を、それが何かを確定するまで一つの単位として記録したもの
- [要望](/concepts/wish.md) — 「〇〇したい」
- [要求](/concepts/requirement.md) — 「（利用者が）〇〇ができる」
- [要件](/concepts/specification.md) — 「（システムが）〇〇をする」
- [契約](/concepts/contract.md) — 要件と開発オブジェクトの間に置く、ER図・Swagger 等を単位とした取り決め
- [成果物ツリー](/concepts/product-tree.md) — プロダクト → システム → コンポーネント → 開発オブジェクト

## 課題

- [未決事項](/open-issues.md) — 今後検討する論点
