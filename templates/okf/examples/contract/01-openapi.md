---
type: 機能契約
id: CTR-F-001
revision: 1
title: 予約API
provider: /structure/CMP-0102.md
format: OpenAPI
thickness: 厚い
elements: [GET /reservations, POST /reservations, "DELETE /reservations/{reservationId}"]
status: draft
tags: [予約, 公開API]
---

> 例：全レスポンスと共通のエラー形式・認証を OpenAPI に書き、方式と互換性は本文の文章で補う（題材：予約API）

# CTR-F-001：予約API

## 当事者と方式

| 項目 | 内容 |
|---|---|
| 提供側 | CMP-0102 予約API（SYS-01 予約アプリ）。オペレーションごとの実装は OBJ-010201〜010203 |
| 利用側 | CMP-0101 予約画面（SPA）、CMP-0301 コールセンター端末（SYS-03） |
| ベース URL | `https://yoyaku.example.jp/api/v1` |
| 認証 | ID 基盤（SYS-04）が発行するアクセストークン（JWT、有効 15 分）を `Authorization: Bearer` で送る |
| 冪等性 | `POST /reservations` は `Idempotency-Key`（UUID）必須。同じキーの再送には 24 時間、最初の結果を返す |
| 流量制限 | 利用者ごとに毎分 60 回。超えたら 429 と `Retry-After` |
| データ量の上限 | 本文 64 KB。一覧は 1 ページ最大 50 件 |
| 日時 | ISO 8601、オフセット付き（`+09:00`）。SYS-01 共通方針 |

## 互換性

- 後方互換とみなす変更：任意項目・任意パラメータの追加、レスポンス項目の追加、エラーコードの追加。利用側は知らない項目を無視する。
- 破壊的変更：項目の削除・改名・型変更、必須化、列挙値の削除、ステータスコードの変更。破壊的変更はパスの版を上げ（`/api/v2`）、旧版を 6 か月並行して提供する。
- 改版のたびに `info.version` を上げ、破壊的かどうかを `log.md` に書く。

## 定義

```yaml
openapi: 3.1.0
info: { title: 予約API, version: 1.0.0 }
servers: [{ url: https://yoyaku.example.jp/api/v1 }]
security: [{ bearerAuth: [] }]
paths:
  /reservations:
    get:
      operationId: listReservations
      summary: 自分の予約を一覧する（来店日の昇順）
      parameters:
        - { name: from, in: query, required: false, schema: { type: string, format: date }, description: 省略時は今日 }
        - { name: cursor, in: query, required: false, schema: { type: string } }
        - { name: limit, in: query, required: false, schema: { type: integer, minimum: 1, maximum: 50, default: 20 } }
      responses:
        "200":
          description: 一覧
          content:
            application/json:
              schema:
                type: object
                required: [items]
                properties:
                  items: { type: array, items: { $ref: "#/components/schemas/Reservation" } }
                  nextCursor: { type: [string, "null"], description: 次がなければ null }
        "400": { $ref: "#/components/responses/BadRequest" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "429": { $ref: "#/components/responses/TooManyRequests" }
        "500": { $ref: "#/components/responses/InternalError" }
    post:
      operationId: createReservation
      summary: 予約する
      parameters:
        - { name: Idempotency-Key, in: header, required: true, schema: { type: string, format: uuid } }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [storeId, slotId, partySize]
              properties:
                storeId: { type: string, pattern: "^S[0-9]{4}$" }
                slotId: { type: string }
                partySize: { type: integer, minimum: 1, maximum: 8 }
                note: { type: string, maxLength: 200 }
      responses:
        "201":
          description: 予約した
          headers: { Location: { schema: { type: string } } }
          content: { application/json: { schema: { $ref: "#/components/schemas/Reservation" } } }
        "200": { description: 冪等キーが同じ再送。最初の結果を返す, content: { application/json: { schema: { $ref: "#/components/schemas/Reservation" } } } }
        "400": { $ref: "#/components/responses/BadRequest" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "409": { description: "枠が埋まった（code: SLOT_FULL）か、同じ日に予約済み（code: DUPLICATE_DAY）", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
        "429": { $ref: "#/components/responses/TooManyRequests" }
        "500": { $ref: "#/components/responses/InternalError" }
  /reservations/{reservationId}:
    delete:
      operationId: cancelReservation
      summary: 予約を取り消す（来店日の前日 23:59 まで）
      parameters:
        - { name: reservationId, in: path, required: true, schema: { type: string, pattern: "^R[0-9]{10}$" } }
      responses:
        "204": { description: 取り消した（取り消し済みでも 204） }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "404": { description: 自分の予約にない, content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
        "422": { description: "期限を過ぎた（code: CANCEL_CLOSED）", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
        "429": { $ref: "#/components/responses/TooManyRequests" }
        "500": { $ref: "#/components/responses/InternalError" }
components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
  schemas:
    Reservation:
      type: object
      required: [reservationId, storeId, slotStartAt, partySize, status]
      properties:
        reservationId: { type: string }
        storeId: { type: string }
        slotStartAt: { type: string, format: date-time }
        partySize: { type: integer }
        note: { type: string }
        status: { type: string, enum: [予約中, 取消] }
    Error:
      type: object
      required: [code, message]
      properties:
        code: { type: string, description: 機械判定用（例：SLOT_FULL） }
        message: { type: string, description: 利用者に見せてよい文言 }
        details: { type: array, items: { type: object, properties: { field: { type: string }, reason: { type: string } } } }
        traceId: { type: string, description: 問い合わせ用 }
  responses:
    BadRequest: { description: "入力の誤り（code: INVALID_INPUT、details に項目）", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    Unauthorized: { description: トークンがない・期限切れ, content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    TooManyRequests: { description: 流量制限, headers: { Retry-After: { schema: { type: integer } } }, content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    InternalError: { description: 想定外の失敗（502・503・504 はロードバランサーが返す場合がある）, content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
```
