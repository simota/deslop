# Create an invoice

`POST /v1/invoices`

Creates a draft invoice for an existing customer. Creating an invoice does not send it to the customer or charge a payment method.

## Authentication

Include a bearer token with permission to create invoices:

```http
Authorization: Bearer YOUR_API_KEY
```

## Headers

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes | Bearer API key. |
| `Content-Type` | Yes | Must be `application/json`. |
| `Idempotency-Key` | No | Unique key for safely retrying a request. Reusing a key with a different request body returns `409 Conflict`. |

## Request body

| Parameter | Type | Required | Description |
|---|---|---|---|
| `customer_id` | string | Yes | ID of the customer to invoice. |
| `currency` | string | Yes | Supported three-letter ISO 4217 currency code, in lowercase, such as `usd`. Applies to all line items. |
| `line_items` | array of objects | Yes | One or more invoice line items. See below. |
| `due_date` | string | No | Payment due date in `YYYY-MM-DD` format. Must not precede the creation date in UTC. |
| `description` | string | No | Description of the invoice. |
| `metadata` | object | No | Custom key-value pairs. Keys and values must be strings. Do not include sensitive payment information. |

Omit optional fields when unused; `null` values are not accepted.

### Line items

| Parameter | Type | Required | Description |
|---|---|---|---|
| `description` | string | Yes | Nonempty description of the item or service. |
| `quantity` | integer | Yes | Number of units. Must be greater than zero. |
| `unit_amount` | integer | Yes | Price per unit in the currency’s smallest unit. Must be zero or greater. For USD, `2500` represents $25.00. |

Each line item’s amount equals `quantity × unit_amount`. The invoice total is the sum of all line item amounts. This endpoint does not apply taxes or discounts.

## Request example

```bash
curl -X POST "https://api.example.com/v1/invoices" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: invoice-cus_123-2026-11" \
  -d '{
    "customer_id": "cus_123",
    "currency": "usd",
    "line_items": [
      {
        "description": "Monthly subscription",
        "quantity": 1,
        "unit_amount": 2500
      },
      {
        "description": "Additional seats",
        "quantity": 2,
        "unit_amount": 1000
      }
    ],
    "due_date": "2026-11-30",
    "description": "November subscription",
    "metadata": {
      "order_id": "ord_456"
    }
  }'
```

## Response

Returns `201 Created` with the invoice object.

```json
{
  "id": "inv_789",
  "customer_id": "cus_123",
  "status": "draft",
  "currency": "usd",
  "line_items": [
    {
      "id": "ili_001",
      "description": "Monthly subscription",
      "quantity": 1,
      "unit_amount": 2500,
      "amount": 2500
    },
    {
      "id": "ili_002",
      "description": "Additional seats",
      "quantity": 2,
      "unit_amount": 1000,
      "amount": 2000
    }
  ],
  "total": 4500,
  "amount_paid": 0,
  "amount_due": 4500,
  "due_date": "2026-11-30",
  "description": "November subscription",
  "metadata": {
    "order_id": "ord_456"
  },
  "created_at": "2026-11-01T09:00:00Z"
}
```

### Response fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique invoice ID. |
| `customer_id` | string | Customer associated with the invoice. |
| `status` | string | `draft` for newly created invoices. |
| `currency` | string | Currency used for every monetary amount. |
| `line_items` | array of objects | Submitted line items, each with a generated `id` and calculated `amount`. |
| `total` | integer | Sum of line item amounts, in the currency’s smallest unit. |
| `amount_paid` | integer | Amount paid. Initially `0`. |
| `amount_due` | integer | Outstanding amount. Initially equal to `total`. |
| `due_date` | string or null | Payment due date, or `null` if omitted. |
| `description` | string or null | Invoice description, or `null` if omitted. |
| `metadata` | object | Custom key-value pairs. Defaults to `{}`. |
| `created_at` | string | Creation timestamp in RFC 3339 format, in UTC. |

## Errors

Errors return a JSON object with a stable error code and a human-readable message.

```json
{
  "error": {
    "code": "validation_error",
    "message": "Quantity must be greater than zero.",
    "param": "line_items[0].quantity",
    "request_id": "req_abc123"
  }
}
```

`param` identifies the invalid field and is `null` when the error does not apply to a specific field. Include `request_id` when contacting support.

| HTTP status | Error code | Description |
|---|---|---|
| `400 Bad Request` | `invalid_request` | The request body contains malformed JSON. |
| `401 Unauthorized` | `authentication_required` | The bearer token is missing, invalid, or expired. |
| `403 Forbidden` | `permission_denied` | The token does not have permission to create invoices. |
| `404 Not Found` | `customer_not_found` | The customer does not exist in the authenticated account. |
| `409 Conflict` | `idempotency_conflict` | The idempotency key was previously used with a different request body. |
| `422 Unprocessable Entity` | `validation_error` | A required field is missing or a value is invalid, including an unsupported currency or an empty line item list. |
| `429 Too Many Requests` | `rate_limit_exceeded` | The request rate limit was exceeded. |
| `500 Internal Server Error` | `internal_error` | An unexpected server error occurred. |

### Retrying requests

For network failures or `5xx` responses, retry with exponential backoff and the same `Idempotency-Key` and request body to avoid creating duplicate invoices. For `429` responses, honor the `Retry-After` header before retrying. Correct other `4xx` errors before submitting another request.