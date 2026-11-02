# RFC: Internal Feature-Flag Service

| Field | Value |
|---|---|
| **Status** | Draft |
| **Author(s)** | _TBD_ |
| **Reviewers** | Platform, SRE, Security, representative product teams |
| **Created** | 2026-11-01 |
| **Target decision date** | _TBD_ |

---

## 1. Summary

This RFC proposes an internal feature-flag service (working name: **Flagd**) to replace the boolean and enum flags currently hard-coded in per-service config files. The service gives us one source of truth for flag definitions, lets us change flags at runtime without a redeploy, supports targeted rollouts (by percentage, tenant, user, or environment), and keeps an audit log of every change. Services read flags through a thin SDK. The SDK evaluates flags locally from a cached ruleset, so a flag lookup never needs a network call and keeps working if the service goes down.

## 2. Motivation

### 2.1 Current state

Feature flags currently live in YAML/JSON/env config files that ship with each service (for example `config/production.yaml`, `.env.production`, Helm values). This has several consequences:

- **Changing a flag means a deploy.** Turning a feature on or off goes through PR, review, CI, and rollout. During an incident this turns a seconds-long kill switch into a 20–60 minute process.
- **No gradual rollout.** Flags are all-or-nothing per environment. We can't run a 1% canary, enable a feature for internal users only, or ramp up by tenant without writing custom code each time.
- **Flags are scattered and drift apart.** One logical feature that spans several services needs coordinated edits in several repos. The values drift between services and environments, and nobody can reliably say what is on in production.
- **Weak auditability.** Git history shows *what* changed in a file. It doesn't easily show *when the change took effect*, who approved it as a flag change, or which flags were live during an incident window.
- **Stale flags pile up.** Nothing tracks flag ownership or age, so dead flags and dead code paths stay around indefinitely.

### 2.2 Goals

1. Change flags at runtime, with propagation to all consumers in **≤ 30 seconds (p99)**.
2. Targeting rules: environment, percentage rollout (sticky by key), and allow/deny lists on arbitrary context attributes (user ID, tenant ID, region, app version).
3. Evaluation stays fast and highly available, and **flag reads never take down a service**.
4. A full audit trail of who changed what, when, and why, plus a way to roll back.
5. A flag lifecycle (owner, type, expiry) with tooling to find and remove stale flags.
6. A low-effort migration path from existing config-file flags.

### 2.3 Non-goals

- **Experimentation/A-B analytics.** We emit exposure events but don't build statistical analysis here. That may be a follow-up RFC.
- **General dynamic configuration.** This isn't a replacement for secrets management or arbitrary service config (connection strings, timeouts). Flags are limited to boolean, string-enum, and small JSON variants.
- **Customer-facing flag management.** The service is internal only.
- **Client-side (browser/mobile) evaluation in v1.** That's covered in Future Work.

## 3. Proposal

### 3.1 Concepts

| Concept | Description |
|---|---|
| **Flag** | A named key (e.g. `checkout.new-payment-flow`) with a type, a set of variants, a default variant, an owner, and an optional expiry date. |
| **Variant** | A possible value: `on`/`off` for booleans, or named values for enums/JSON. |
| **Environment** | `dev`, `staging`, `production`, and so on. Each flag has independent rules per environment. |
| **Rule** | An ordered condition → variant mapping, evaluated top-down. The first match wins. If nothing matches, the default applies. |
| **Context** | Attributes the caller passes at evaluation time (`user_id`, `tenant_id`, `region`, `app_version`, …). |
| **Segment** | A reusable, named set of conditions (e.g. `internal-staff`, `beta-tenants`). |

### 3.2 Architecture

```
            ┌──────────────────────┐
            │  Admin UI / CLI / API │  (authN via SSO, authZ via RBAC)
            └──────────┬───────────┘
                       │ writes
            ┌──────────▼───────────┐       ┌──────────────┐
            │   Flag Control Plane  │──────▶│  Audit Log   │
            │  (CRUD, validation,   │       └──────────────┘
            │   versioning)         │
            └──────────┬───────────┘
                       │ persists
            ┌──────────▼───────────┐
            │  Primary store (SQL)  │
            └──────────┬───────────┘
                       │ publishes ruleset snapshots + deltas
            ┌──────────▼───────────┐
            │   Distribution layer  │  (streaming endpoint + CDN/object-store snapshot)
            └──────────┬───────────┘
          ┌────────────┼────────────┐
     ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
     │ Svc A   │  │ Svc B   │  │ Svc C   │   SDK: in-memory ruleset,
     │ + SDK   │  │ + SDK   │  │ + SDK   │   local evaluation, disk cache
     └─────────┘  └─────────┘  └─────────┘
```

**Control plane.** A stateless API service that owns flag CRUD, validates rules (schema, references to segments, no unreachable rules), and assigns a monotonically increasing ruleset version on every change. It's the only writer.

**Primary store.** A relational database holding flags, rules, segments, and the version history. Every change is an immutable revision row, which makes rollback and point-in-time queries straightforward.

**Distribution layer.** Two paths:
1. **Streaming** (SSE or gRPC stream): SDKs subscribe per environment and receive deltas tagged with the ruleset version.
2. **Snapshot**: a full ruleset JSON per environment, written to object storage/CDN on every change. SDKs load it at startup and fall back to it if the stream is unavailable.

**SDK.** It holds the full ruleset for its environment in memory and evaluates flags locally in microseconds, with no network call per evaluation. It persists the last known good ruleset to local disk so cold starts work while the service is down. It also buffers exposure/evaluation metrics and flushes them asynchronously.

### 3.3 Evaluation semantics

- Rules are evaluated in order. The first matching rule picks the variant.
- Percentage rollouts use `hash(flag_key + salt + bucketing_key) mod 10000`. The default bucketing key is `user_id`, and it's configurable per rule. This keeps assignment sticky and independent across flags.
- If evaluation fails for any reason (unknown flag, type mismatch, missing context attribute required by a rule), the SDK returns the **code-supplied default** and emits an error metric. It never throws into application code.
- Example SDK usage:

```python
enabled = flags.bool("checkout.new-payment-flow", default=False,
                     context={"user_id": user.id, "tenant_id": tenant.id})
```

```go
variant := flags.String(ctx, "search.ranking-model", "v1",
    flagd.Context{"tenant_id": tenantID})
```

### 3.4 Flag lifecycle and metadata

Every flag must declare:

- `owner` (team, resolvable to an on-call rotation)
- `type`: `release` (temporary), `ops` (kill switch, long-lived), `permission` (entitlement-like, long-lived), or `experiment`
- `expires_at`: required for `release` and `experiment` flags. The default is creation + 90 days.
- `description` and an optional link to a ticket or design doc

Lifecycle tooling:

- Owners get a weekly digest of flags that are expired, or that have served a single variant in production for 30+ days.
- The SDK reports which flags are evaluated, so the service can flag definitions that **no service evaluates anymore**.
- A CI lint step (`flagd lint`) fails builds that reference undefined flags, and warns on references to expired flags.

### 3.5 Change management and safety

- **RBAC.** A flag's owners can edit it in all environments. Others can edit in `dev`/`staging` only. Changes to production `ops` flags are open to on-call as well, so kill switches stay fast during incidents.
- **Optional approval.** Flags marked `requires_review` need a second approver for production changes.
- **Change reason.** Every production change requires a free-text reason, which is recorded in the audit log.
- **Rollback.** One-click or CLI revert to any prior revision of a flag.
- **Change notifications.** Production changes post to a configurable chat channel and are emitted as events for the incident timeline and observability tooling (annotations on dashboards).
- **Scheduled changes** (v1.1): e.g. ramp 1% → 10% → 50% → 100% on a schedule, with automatic pause if a linked alert fires.

### 3.6 Interfaces

- **Admin UI.** Browse and search flags, edit rules, view history and diffs, see per-flag evaluation counts.
- **CLI** (`flagd`). Scriptable management, plus import/export.
- **REST/gRPC API.** For automation and CI.
- **GitOps mode (optional).** Teams that prefer flags-as-code can keep flag definitions in a repo. A sync job applies them through the API, and the UI then shows those flags as read-only with a link to the source. This mode exists to ease migration and is not required.

## 4. Non-functional requirements

| Requirement | Target |
|---|---|
| Evaluation latency (SDK, in-process) | < 50 µs p99 |
| Change propagation to connected SDKs | ≤ 30 s p99 (expected ≤ 5 s) |
| Control-plane availability | 99.9% (writes may degrade during an outage) |
| Evaluation availability | Effectively 100%: evaluation is local and survives a full service outage using the cached ruleset |
| Ruleset size per environment | Designed for ≥ 10,000 flags and ≤ 5 MB snapshot |
| Audit retention | ≥ 2 years (align with compliance policy) |

## 5. Failure modes

| Failure | Behavior |
|---|---|
| Control plane down | No flag changes possible. SDKs keep serving the last ruleset. Alert fires. |
| Streaming endpoint down | SDKs fall back to polling the snapshot every 30–60 s. |
| Snapshot and stream both unreachable at startup | SDK loads its on-disk cache. If there's no cache, it serves code defaults and reports `flagd_ruleset_missing`. |
| Bad rule pushed | Rejected by validation where possible. Otherwise rolled back via revision history. Propagation is the same as for any change. |
| Ruleset version regression (stale delta) | SDK ignores deltas older than its current version and resyncs from the snapshot. |

## 6. Security and privacy

- Admin access goes through company SSO. RBAC is mapped to existing team groups.
- SDKs authenticate with per-service, per-environment read-only tokens issued through our existing secrets management. They can't write.
- Context attributes are evaluated in-process and **never sent to the flag service**. Exposure metrics carry only flag key, variant, and counts by default, with no user identifiers unless a flag is explicitly marked `experiment` and the team has opted in.
- Rulesets can contain allowlisted IDs (e.g. tenant IDs), so snapshots are stored in private buckets and not exposed publicly.

## 7. Migration plan

**Phase 0: Inventory (2 weeks).** A script scans repos for flag-like keys in config files (`*_enabled`, `feature_*`, `FF_*`, and similar). The output is a spreadsheet with service, key, per-environment values, and a guessed owner. Teams confirm or discard each entry.

**Phase 1: Platform MVP (6–8 weeks).** Control plane, store, snapshot distribution, polling-based SDKs for our two primary languages, CLI, basic UI, and audit log. Pilot with 2–3 volunteer teams.

**Phase 2: Dual-read (per service).** The SDK is wrapped in a config-file fallback: `flagd value if defined, else config-file value`. We import the existing values with `flagd import`, then verify parity through a shadow-comparison metric that logs mismatches between the config value and the flag service value.

**Phase 3: Cutover.** Once parity has held for ≥ 1 week, remove the flag from config files. The flag service becomes authoritative.

**Phase 4: Enforcement.** A CI lint rule blocks new flag-like keys in config files. Streaming distribution, segments, and scheduled rollouts ship.

Teams aren't forced to migrate all flags at once. Long-lived `ops` kill switches are the highest priority because they deliver the incident-response benefit immediately.

## 8. Alternatives considered

### 8.1 Status quo (config files)
No new infrastructure, but it leaves every problem in §2.1 unsolved. Rejected.

### 8.2 Centralized config repo with fast deploy
One Git repo for all flags, with a pipeline that pushes changes to services within minutes. This improves consistency and auditability, but targeting, percentage rollouts, and kill-switch speed still depend on a CI pipeline. Partially adopted as the optional GitOps mode (§3.6).

### 8.3 Commercial SaaS (e.g. LaunchDarkly, Split, Statsig, ConfigCat)
- **Pros:** Mature, feature-rich, no build cost, experimentation included.
- **Cons:** Per-seat or per-MAU cost that grows with us. Context data and rulesets go to a third party, which needs a privacy and vendor review. We'd depend on an external vendor for a control path that touches every service.
- **Assessment:** A legitimate option. See Open Question 1. A cost comparison over 3 years should be completed before the decision date.

### 8.4 Self-hosted open source (e.g. Unleash, Flagsmith, GrowthBook, flagd/OpenFeature)
- **Pros:** No license cost, data stays internal, existing SDKs.
- **Cons:** Operational ownership, and possibly a mismatch with our RBAC/audit requirements.
- **Assessment:** **Strongly preferred over a full in-house build** if one of them meets §2.2 and §3.5. Recommendation: run a 2-week evaluation spike before Phase 1, and build only the missing pieces (SSO/RBAC integration, lifecycle tooling, migration tooling).

### 8.5 Adopt OpenFeature as the SDK interface regardless of backend
We recommend this whichever backend we choose. Application code depends on the vendor-neutral OpenFeature API, and the provider can be swapped later (in-house, OSS, or SaaS) without touching call sites.

## 9. Costs and ownership

- **Owning team:** Platform Engineering (proposed). The service is tier-1 for the control path, but evaluation is local, so an outage degrades flag *changes*, not product traffic.
- **Build estimate:** About 2 engineers for 1 quarter for Phases 0–2 if we build on an OSS core. Roughly double that for a fully in-house build.
- **Run cost:** One small stateless service, one small SQL instance, object storage, and a streaming endpoint. Expected to be negligible relative to current infra spend. _Exact figures TBD._
- **Ongoing:** On-call coverage, SDK maintenance for each supported language.

## 10. Success metrics

- Median time to toggle a production flag drops from deploy time (~30+ min) to **< 1 min**.
- ≥ 90% of identified config-file flags migrated within 2 quarters of GA.
- Zero incidents caused by flag-service unavailability affecting product traffic.
- The stale-flag count (expired and still referenced) trends downward quarter over quarter.
- At least one incident per quarter mitigated by a kill switch instead of a rollback or hotfix. This is a leading indicator of adoption.

## 11. Open questions

1. **Build vs. buy vs. OSS.** Do we commit to an OSS core with internal extensions (recommended), or does the SaaS cost comparison change the answer?
2. **Language coverage.** Which SDKs are required for GA beyond the two primary languages?
3. **Approval policy.** Should second-approver review be the default for production, or opt-in per flag?
4. **Client-side flags.** Do mobile and web clients need flags in v1? If so, we need a server-side evaluation proxy so rulesets aren't exposed to clients.
5. **Expiry enforcement.** Do expired `release` flags only warn, or eventually fail CI?

## 12. Future work

- Client-side evaluation via an edge/proxy evaluation endpoint.
- Experimentation analytics built on exposure events.
- Automated rollout guardrails tied to SLO burn-rate alerts.
- IDE plugin showing flag status inline at call sites.

---

_Feedback: please leave comments on this document or in the RFC review thread by the target decision date._
