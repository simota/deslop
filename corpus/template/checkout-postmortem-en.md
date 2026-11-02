# Postmortem: Checkout outage caused by a locking schema migration

- **Date of incident:** [YYYY-MM-DD]
- **Duration:** about 40 minutes ([HH:MM] to [HH:MM] [timezone])
- **Severity:** [SEV-1 / SEV-2]
- **Status:** [Draft / Reviewed]
- **Author:** [name]
- **Incident commander:** [name]

## Summary

A database schema migration on the `[table_name]` table took a lock that blocked reads and writes. Checkout requests queued behind the lock, exhausted the connection pool, and timed out. Customers could not complete purchases for about 40 minutes. The incident ended when we [killed the migration session / rolled back the migration], which released the lock. No data was lost. [Confirm.]

## Impact

- Checkout was unavailable or failing for about 40 minutes.
- [N] checkout attempts failed, based on [source: error logs / payment provider dashboard].
- Estimated lost orders: [N], worth about [amount]. [State how this was estimated, or write "not yet measured".]
- [Number of support tickets, if any.]
- [Other services affected by the exhausted pool, if any.]

## Timeline

All times are [timezone].

| Time | Event |
|---|---|
| [HH:MM] | Migration `[migration_id]` started as part of [deploy / manual run]. |
| [HH:MM] | The migration's `ALTER TABLE` acquired (or began waiting for) a lock on `[table_name]`. |
| [HH:MM] | Checkout error rate and latency rose. |
| [HH:MM] | Alert `[alert_name]` fired. |
| [HH:MM] | Incident declared. [Name] became incident commander. |
| [HH:MM] | Lock contention identified as the cause, using [pg_stat_activity / SHOW PROCESSLIST / equivalent]. |
| [HH:MM] | Migration session [terminated / rolled back]. |
| [HH:MM] | Locks cleared. Connection pool began recovering. |
| [HH:MM] | Checkout error rate returned to baseline. Incident closed. |

## Root cause

The migration [adds a column with a default / adds an index without concurrent build / changes a column type / adds a constraint] on `[table_name]`. On [database and version], this operation [takes an ACCESS EXCLUSIVE lock / rewrites the table] for as long as it runs. `[table_name]` is read and written on every checkout, so every request that touched it waited on the lock.

[If applicable: the migration first waited behind a long-running transaction, and while it waited it blocked all later queries on the table. This is how a short DDL statement can stall a table before it does any work.]

Waiting requests held their database connections. The pool filled, and requests that did not need the table also began to fail because no connection was free.

## Detection

- The first signal was [alert name / customer report / dashboard], at [HH:MM], [N] minutes after the migration started.
- [Say whether this was fast enough. If detection was late, say why.]

## Response

- [Who was paged, and how long they took to engage.]
- [What was tried first and why it did not work, if anything.]
- The lock was released by [exact action]. Ending the migration was the fix. [State whether the migration was later re-run, and how.]

## Contributing factors

- **Review:** The migration was reviewed for correctness but not for its locking behaviour. [Confirm.]
- **Staging:** The migration ran in staging against [a small table / no concurrent traffic], so the lock was not noticeable there.
- **Timing:** The migration ran at [time], during [peak / normal] checkout traffic.
- **Safeguards:** No `lock_timeout` or `statement_timeout` was set for the migration session, so it waited and held locks without limit.
- **Pool:** The checkout service has no timeout short enough to fail fast when the database stalls, so the pool drained.
- **Alerting:** [Gap in alerting, if any.]

## What went well

- [Item.]
- [Item.]

## What went poorly

- Detection took [N] minutes.
- It took [N] minutes from detection to identifying the migration as the cause.
- [Item.]

## Action items

| Action | Owner | Priority | Due | Ticket |
|---|---|---|---|---|
| Set `lock_timeout` and `statement_timeout` on all migration sessions so a blocked migration fails instead of waiting. | [name] | P0 | [date] | [link] |
| Add a CI check that flags migrations known to take heavy locks (table rewrites, non-concurrent index builds, new constraints) on tables above [size]. | [name] | P1 | [date] | [link] |
| Add a migration review checklist item: state the lock taken and the expected duration at production table size. | [name] | P1 | [date] | [link] |
| Test migrations against a production-sized copy of the data under load before release. | [name] | P2 | [date] | [link] |
| Run migrations on high-traffic tables outside peak hours, with an on-call engineer watching. | [name] | P1 | [date] | [link] |
| Set connection acquisition and query timeouts in the checkout service so a database stall does not exhaust the pool. | [name] | P1 | [date] | [link] |
| Alert on lock wait time and on checkout error rate with a threshold that would have fired within [N] minutes. | [name] | P1 | [date] | [link] |
| Write a runbook for finding and killing a blocking migration session. | [name] | P2 | [date] | [link] |

## Open questions

- [Question that the investigation has not yet answered.]

## Appendix

- Migration file: [link]
- Dashboards and logs for the incident window: [links]
- Incident channel: [link]
