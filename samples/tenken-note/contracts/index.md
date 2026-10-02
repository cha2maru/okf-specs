# 契約

## 機能契約

| ID | 名称 | 提供 | 形式 | 厚さ |
|---|---|---|---|---|
| [CTR-F-001](/contracts/CTR-F-001.md) | 点検API | CMP-0201 | OpenAPI | 厚い（システム間） |
| [CTR-F-002](/contracts/CTR-F-002.md) | ローカルストア | CMP-0102 | 端末内スキーマ | 薄い |
| [CTR-F-003](/contracts/CTR-F-003.md) | 点検DB | CMP-0204 | ER図 | 厚い |
| [CTR-F-004](/contracts/CTR-F-004.md) | 管理API | CMP-0202 | OpenAPI | 厚い（システム間） |
| [CTR-F-005](/contracts/CTR-F-005.md) | メール送信 | CMP-0501 | 外部API仕様 | 厚い（外部） |
| [CTR-F-006](/contracts/CTR-F-006.md) | 写真ストレージ | CMP-0205 | キー規約 | 薄い |
| [CTR-F-007](/contracts/CTR-F-007.md) | 異常イベント | CMP-0203 | メッセージ定義 | 薄い |
| [CTR-F-008](/contracts/CTR-F-008.md) | DB接続 | CMP-0402（IaC） | 接続情報定義 | 厚い（システム間） |
| [CTR-F-009](/contracts/CTR-F-009.md) | 写真バケット | CMP-0403（IaC） | 接続情報定義 | 厚い（システム間） |

## 非機能契約

| ID | 名称 | 品質特性 | 目標 |
|---|---|---|---|
| [CTR-N-001](/contracts/CTR-N-001.md) | ダッシュボード応答性能 | 性能効率性 | 3 秒以内 |
| [CTR-N-002](/contracts/CTR-N-002.md) | 異常通知の即時性 | 性能効率性 | 5 分以内 |
| [CTR-N-003](/contracts/CTR-N-003.md) | クラウド可用性 | 可用性 | 99.5% |
| [CTR-N-004](/contracts/CTR-N-004.md) | 点検データ保護 | セキュリティ | 暗号化 |
