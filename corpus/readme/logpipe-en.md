# logpipe

logpipe tails several log files at once and merges their lines into a single stream, ordered by timestamp. Point it at the files you care about and read one chronological view of what happened across services, instead of switching between `tail -f` sessions.

It is written in Go and ships as a single static binary with no runtime dependencies.

## Why

When a request crosses three services, the evidence is split across three files. Each file is ordered on its own, but the interleaving is what you need to debug. logpipe reads the files concurrently, parses a timestamp from each line, and emits lines in time order, tagging each one with the file it came from.

## Install

With a Go toolchain (1.22 or later):

```sh
go install github.com/<owner>/logpipe/cmd/logpipe@latest
```

Or download a prebuilt binary for Linux, macOS or Windows from the [releases page](https://github.com/<owner>/logpipe/releases).

## Usage

```sh
logpipe [flags] FILE [FILE ...]
```

Merge two files and print the full history:

```sh
logpipe api.log worker.log
```

Follow several files live, as `tail -f` does:

```sh
logpipe -f api.log worker.log db.log
```

Label each line with a short name instead of the file path:

```sh
logpipe -f --label api=api.log --label worker=worker.log
```

Start from the last 200 lines of each file rather than the beginning:

```sh
logpipe -n 200 -f api.log worker.log
```

### Output

Each merged line is prefixed with its source and kept otherwise unchanged:

```
2026-10-30T09:14:02.118Z api     GET /orders/42 started
2026-10-30T09:14:02.131Z worker  job=991 picked up
2026-10-30T09:14:02.407Z api     GET /orders/42 500 in 289ms
```

Lines that carry no recognisable timestamp are kept in place. They inherit the timestamp of the previous line from the same file, so a stack trace stays together.

### Flags

| Flag | Default | Description |
| --- | --- | --- |
| `-f`, `--follow` | off | Keep reading the files as they grow and emit new lines as they arrive. |
| `-n`, `--lines N` | all | Start from the last N lines of each file. |
| `--label NAME=PATH` | file name | Use NAME as the source tag for PATH. Repeatable. |
| `--time-format FMT` | auto | Go time layout for parsing timestamps. Auto-detection covers RFC 3339, ISO 8601 with a space separator, and Unix epoch seconds or milliseconds. |
| `--color` | auto | `always`, `never` or `auto`. Colours each source tag. |
| `--no-prefix` | off | Omit the source tag and print only the lines. |
| `-o`, `--output FILE` | stdout | Write the merged stream to FILE. |
| `-h`, `--help` | | Show help and exit. |
| `--version` | | Print the version and exit. |

## How it works

1. Each input file gets a reader goroutine that parses timestamps and sends records onto a channel.
2. A merge step holds one pending record per file in a min-heap keyed by timestamp and emits the earliest.
3. In `--follow` mode, a reader that reaches end of file waits for growth. It handles rotation by reopening a path when its inode changes.

The merge keeps a small window to absorb clock skew between sources. Records that arrive later than that window are still emitted, but out of order, and a warning is printed to stderr once per source.

## Limitations

- Ordering depends on the timestamps in the logs. Files without timestamps are not merged; they are rejected at startup.
- Timestamps are compared as absolute instants. Files written in different time zones without an offset will merge incorrectly.
- Very high-volume files can fill the merge window faster than the output can drain, which increases memory use. Limit the input with `-n` or split the job.

## Development

```sh
git clone https://github.com/<owner>/logpipe
cd logpipe
go test ./...
go build ./cmd/logpipe
```

Pull requests are welcome. Please include a test for any change to timestamp parsing or merge ordering, since those are where regressions are most likely.

## License

Released under the MIT License. See [LICENSE](LICENSE).
