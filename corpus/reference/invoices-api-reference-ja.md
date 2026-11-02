# 請求書の作成

`POST /v1/invoices`

請求書を下書きとして作成します。この操作では、請求書の送信や支払いの実行は行いません。

> 本ページは仕様例です。実際のAPI仕様が未提示のため、以下のフィールドと動作を仮定しています。

## 認証

Bearerトークンを指定します。

```http
Authorization: Bearer YOUR_API_KEY
```

## リクエストヘッダー

| ヘッダー | 必須 | 説明 |
|---|---|---|
| `Authorization` | はい | `Bearer YOUR_API_KEY` |
| `Content-Type` | はい | `application/json` |
| `Idempotency-Key` | いいえ | 再試行時の重複作成を防ぐ一意のキー。最大255文字。 |

同じキーと同じリクエスト本文を24時間以内に再送した場合、最初の成功時と同じステータスコードとレスポンス本文を返します。同じキーで異なる本文を送信した場合は、`409 Conflict`を返します。

## リクエストパラメーター

本文にJSONオブジェクトを指定します。

| パラメーター | 型 | 必須 | 説明 |
|---|---|---|---|
| `customer_id` | string | はい | 認証されたアカウントに属する既存顧客のID。 |
| `currency` | string | はい | 対応するISO 4217通貨コード。小文字で指定します。例：`usd`、`jpy`。 |
| `line_items` | array of objects | はい | 請求明細。1〜100件。 |
| `due_date` | string | いいえ | 支払期限。`YYYY-MM-DD`形式。省略時は`null`。 |
| `description` | string | いいえ | 請求書の説明。最大1,000文字。 |

### 明細のパラメーター

| パラメーター | 型 | 必須 | 説明 |
|---|---|---|---|
| `line_items[].description` | string | はい | 明細の説明。1〜500文字。 |
| `line_items[].quantity` | integer | はい | 数量。1〜1,000,000。 |
| `line_items[].unit_amount` | integer | はい | 通貨の最小単位で指定する単価。0以上。 |

金額に小数は使用できません。たとえば、USDの`2500`は25.00米ドル、JPYの`2500`は2,500円です。すべての明細に請求書の`currency`が適用されます。

各明細の金額は`quantity × unit_amount`、請求書の合計額は明細金額の合計です。この仕様例では税金と割引は扱いません。合計額は`9,007,199,254,740,991`以下である必要があります。

未知のパラメーターと、任意パラメーターへの明示的な`null`は受け付けません。値を指定しない場合は、そのパラメーターを省略してください。

## リクエスト例

```bash
curl https://api.example.com/v1/invoices \
  --request POST \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --header "Idempotency-Key: 7e590e87-5370-46a8-9954-a62e8a24f194" \
  --data '{
    "customer_id": "cus_123",
    "currency": "usd",
    "due_date": "2026-12-01",
    "description": "November services",
    "line_items": [
      {
        "description": "Monthly subscription",
        "quantity": 1,
        "unit_amount": 2500
      },
      {
        "description": "Additional seats",
        "quantity": 3,
        "unit_amount": 500
      }
    ]
  }'
```

## レスポンス

成功時は`201 Created`と、作成した請求書を返します。

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /v1/invoices/inv_456
```

```json
{
  "id": "inv_456",
  "customer_id": "cus_123",
  "status": "draft",
  "currency": "usd",
  "description": "November services",
  "due_date": "2026-12-01",
  "line_items": [
    {
      "description": "Monthly subscription",
      "quantity": 1,
      "unit_amount": 2500,
      "amount": 2500
    },
    {
      "description": "Additional seats",
      "quantity": 3,
      "unit_amount": 500,
      "amount": 1500
    }
  ],
  "total": 4000,
  "created_at": "2026-11-01T09:00:00Z"
}
```

### レスポンスフィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string | 請求書の一意のID。 |
| `customer_id` | string | 請求先顧客のID。 |
| `status` | string | 作成直後は`draft`。 |
| `currency` | string | 請求書の通貨。 |
| `description` | string or null | 請求書の説明。未指定時は`null`。 |
| `due_date` | string or null | 支払期限。未指定時は`null`。 |
| `line_items` | array of objects | 作成された明細。リクエストと同じ順序。 |
| `line_items[].description` | string | 明細の説明。 |
| `line_items[].quantity` | integer | 数量。 |
| `line_items[].unit_amount` | integer | 通貨の最小単位で表した単価。 |
| `line_items[].amount` | integer | 数量と単価から計算した明細金額。 |
| `total` | integer | 通貨の最小単位で表した請求書の合計額。 |
| `created_at` | string | UTCの作成日時。RFC 3339形式。 |

## エラー

エラーは共通のJSON形式で返します。

```json
{
  "error": {
    "code": "validation_error",
    "message": "Quantity must be an integer greater than or equal to 1.",
    "param": "line_items[0].quantity",
    "request_id": "req_789"
  }
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `error.code` | string | プログラムで判定するためのエラーコード。 |
| `error.message` | string | エラーの説明。文言は変更される場合があります。 |
| `error.param` | string or null | 問題のあるパラメーター。特定できない場合は`null`。 |
| `error.request_id` | string | 問い合わせや調査に使用するリクエストID。 |

### ステータスコード

| HTTPステータス | エラーコード | 原因・対応 |
|---|---|---|
| `400 Bad Request` | `invalid_json` | JSONを解析できません。本文の構文を修正してください。 |
| `401 Unauthorized` | `authentication_required` | APIキーが未指定、無効、または失効しています。 |
| `403 Forbidden` | `permission_denied` | APIキーに請求書作成権限がありません。 |
| `404 Not Found` | `customer_not_found` | 顧客が存在しないか、認証されたアカウントに属していません。 |
| `409 Conflict` | `idempotency_conflict` | 同じ冪等性キーが異なるリクエスト本文で使用されています。 |
| `415 Unsupported Media Type` | `unsupported_media_type` | `Content-Type: application/json`を指定してください。 |
| `422 Unprocessable Content` | `validation_error` | 必須項目の欠落、型・範囲・形式の不正、未対応通貨、未知のパラメーター、または合計額の上限超過です。 |
| `429 Too Many Requests` | `rate_limit_exceeded` | リクエスト上限に達しました。`Retry-After`ヘッダーの秒数を待って再試行してください。 |
| `500 Internal Server Error` | `internal_error` | サーバー内部でエラーが発生しました。間隔を空けて再試行してください。 |
| `503 Service Unavailable` | `service_unavailable` | 一時的に利用できません。`Retry-After`がある場合は、その秒数を待って再試行してください。 |

タイムアウトや`5xx`では、請求書が作成済みの可能性があります。重複作成を防ぐため、最初のリクエストから`Idempotency-Key`を指定し、再試行でも同じキーと本文を使用してください。