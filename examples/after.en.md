# Tile caching

`tilecache` has three cache settings: TTL, capacity and eviction. TTL is set with `ttl_seconds`; the default is 300 seconds. Capacity is set with `max_entries`; the default is 10000 entries.

```toml
[cache]
ttl_seconds = 300
max_entries = 10000
```

See https://example.com/tilecache/docs for details.
