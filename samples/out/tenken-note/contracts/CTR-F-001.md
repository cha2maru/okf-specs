# 契約書　CTR-F-001 点検API

| 項目 | 内容 |
|---|---|
| 契約ID | CTR-F-001 |
| 契約名 | 点検API |
| 種別 | 機能契約 |
| 版 | 1 |
| 状態 | 作成中 |
| 提供 | SYS-02 クラウドバックエンド / CMP-0201 点検API |
| 形式 | OpenAPI |
| 厚さ | 厚い |
| 作成日 | 2026-10-03 |
| 生成元 | OKF バンドル（（導出）の節は取り込み時に無視される） |

## 1. 契約内容

システムをまたぐため厚い契約。

```yaml
openapi: 3.1.0
paths:
  /inspections:
    post:
      summary: 点検結果を登録する
      parameters:
        - { name: Idempotency-Key, in: header, required: true }
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [equipmentId, inspectedAt, items]
              properties:
                equipmentId: { type: string }
                inspectedAt: { type: string, format: date-time }
                items:
                  type: array
                  items: { type: object, properties: { code: {type: string}, result: {enum: [正常, 異常]}, comment: {type: string} } }
      responses: { "201": {}, "200": { description: 冪等キー重複時 } }
  /inspections/{id}/photos/{n}:
    put:
      summary: 点検写真をアップロードする
      requestBody: { content: { image/jpeg: {} } }
```

## 2. 提供コンポーネントの開発オブジェクト（導出）

- OBJ-020101 点検結果登録API（API）
- OBJ-020102 点検写真登録API（API）

## 3. 突合結果（導出）

- 差異なし（OpenAPI のオペレーションと開発オブジェクトが一致）

## 4. 利用者（導出）

| 開発オブジェクト | システム | 参照先 | CRUD | 前提版 | 状態 |
|---|---|---|---|---|---|
| OBJ-010301 同期処理 | モバイルアプリ | OBJ-020101 点検結果登録API、OBJ-020102 点検写真登録API | ― | 1 | 最新 |

## 5. 参照する要件（導出）

| 要件 | 参照先 | 前提版 | 状態 |
|---|---|---|---|
| SPC-003 モバイルアプリは通信回復時に未送信の点検結果と写真を自動送信する | OBJ-020101 点検結果登録API、OBJ-020102 点検写真登録API | 1 | 最新 |
| SPC-004 クラウドは受信した点検結果と写真を保存する | OBJ-020101 点検結果登録API、OBJ-020102 点検写真登録API | 1 | 最新 |

## 6. レビュー

| 確認者 | 確認日時 |
|---|---|
|  |  |

確認観点：

- 突合結果に差異がないか。契約に主従はないため、差異は当事者間の衝突として裁定で解決する
- 利用者の参照先・CRUD が契約内容と矛盾しないか
- 要確認の参照が解消されているか

確認後、確認者と確認日時を記入して取り込むと OKF の verified に反映される。
