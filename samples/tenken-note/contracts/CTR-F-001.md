---
type: 機能契約
id: CTR-F-001
revision: 1
title: 点検API
provider: /structure/CMP-0201.md
format: OpenAPI
thickness: 厚い
elements: [POST /inspections, "PUT /inspections/{id}/photos/{n}"]
status: draft
---

# CTR-F-001：点検API

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
