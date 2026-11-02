# キャッシュ設定

`tilecache` のキャッシュ設定は TTL、容量、退避方式の3項目です。TTL は `ttl_seconds` で指定し、既定値は 300 秒です。容量は `max_entries` で指定し、既定値は 10000 件です。

```toml
[cache]
ttl_seconds = 300
max_entries = 10000
```

詳細は https://example.com/tilecache/docs を参照してください。
