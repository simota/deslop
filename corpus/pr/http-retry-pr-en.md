## Summary

Add retries with exponential backoff to the internal HTTP client, including handling for `429 Too Many Requests` and `503 Service Unavailable` responses. Increasing the delay between attempts gives upstream services time to recover and reduces repeated requests during rate limiting or temporary outages.

## Validation

Verify recovery after transient 429 and 503 responses, increasing delays between attempts, and error propagation when retries are exhausted.