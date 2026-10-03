---
type: 機能契約
id: CTR-F-004
revision: 1
title: 管理API
provider: /structure/CMP-0202.md
format: OpenAPI
thickness: 厚い
elements: [GET /sites/progress]
status: draft
---

# CTR-F-004：管理API

```yaml
openapi: 3.1.0
paths:
  /sites/progress:
    get:
      parameters: [ { name: month, in: query, schema: { type: string, example: "2026-10" } } ]
      responses:
        "200":
          content:
            application/json:
              schema:
                type: array
                items: { type: object, properties: { siteId: {type: string}, name: {type: string}, total: {type: integer}, done: {type: integer} } }
```
