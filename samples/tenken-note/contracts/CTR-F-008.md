---
type: 機能契約
id: CTR-F-008
revision: 1
title: DB接続
provider: /structure/CMP-0402.md
format: 接続情報定義
thickness: 厚い
status: draft
---

# CTR-F-008：DB接続（クラウド基盤 ⇔ クラウドバックエンド）

IaC が提供する DB の接続先。アプリはこの取り決めだけに依存し、クラスタの構成には依存しない。

```yaml
endpoint_env: DB_HOST           # 環境変数名
port: 5432
database: tenken
credentials_secret: tenken/db/app  # シークレット名
```
