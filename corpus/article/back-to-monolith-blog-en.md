# Why we moved from microservices back to a monolith

*Posted by the Platform Team*

Two years ago, we split our product into microservices. Last quarter, we finished merging most of them back into one application.

This post covers why we split the system, what went wrong, how we moved back without stopping feature work, and what we would tell a team of our size today. It is not an argument against microservices. It is an argument against adopting an architecture built for problems you don't have yet.

## A bit of context

We're a 40-person company. About 16 of us are engineers, split across three product teams and a small platform team. We run a B2B SaaS product with a web app, a public API, a few background pipelines, and a handful of integrations with third-party systems.

At our peak, that product ran on **14 services**, each with its own repository, CI pipeline, deploy process, and in most cases its own database.

Today it runs on **one main application, two satellite services, and one shared Postgres cluster.**

## How we got to 14 services

None of the decisions were unreasonable at the time they were made.

- **The original monolith hurt.** Our first codebase had grown fast and without much structure. Tests took 25 minutes, and a change to billing could break onboarding. Deploys were scary, so we batched them, and batching made them scarier.
- **We were hiring quickly.** We expected to double engineering within a year. Service boundaries looked like a way to let new teams work without stepping on each other.
- **It looked like what serious companies do.** Several of us came from larger companies that ran hundreds of services. The pattern was familiar, and in hindsight we mistook familiarity for fit.

So we drew boxes around the domains (accounts, billing, notifications, documents, search, integrations, and so on) and started carving.

## What actually happened

### 1. We kept the coupling and lost the compiler

Our domains were not as independent as the boxes suggested. Most user-facing features touched three or four services. Before, a call between modules was a function call that the type checker verified. Afterwards, it was an HTTP request with a JSON payload that nothing verified until runtime.

A typical feature, such as letting admins bulk-reassign documents, needed changes to `documents`, `accounts`, `notifications`, and `audit-log`. That meant four PRs in four repos, deployed in a specific order. If the order was wrong, things broke in production.

We had built a **distributed monolith**: all the coupling of a monolith, plus network failures.

### 2. Operational overhead scaled with service count, not team size

Each service needed:

- A CI pipeline
- Dockerfiles and base image updates
- Kubernetes manifests, autoscaling config, and resource limits
- Dashboards, alerts, and an on-call runbook
- Dependency upgrades and security patches
- Secrets, service accounts, and network policies

Multiplied by 14, that was a lot of work for a platform team of **two people**. We once measured how much engineering time went to keeping services healthy rather than shipping product. It came out at roughly **30% of total engineering capacity**. For a startup still searching for its next growth curve, that was too much.

### 3. Debugging got much harder

A customer reporting "the export is stuck" used to mean one stack trace. Now it meant tracing a request through an API gateway, three services, and a queue, across logs in several places. We invested in distributed tracing, and it helped, but tracing was another system to run and keep correctly instrumented.

Our median time to resolve a production incident went from **under an hour to around three hours** during the microservices period. Few of those incidents were hard bugs. Most of the time went into working out *where* the bug was.

### 4. Data consistency became our problem to solve

When billing and accounts shared a database, "create a subscription and upgrade the account" was one transaction. When they were separate services with separate databases, it became a saga with compensating actions, retries, and idempotency keys.

We implemented this carefully in some places and less carefully in others. The less careful places produced a slow trickle of customers whose plan in billing didn't match their plan in accounts. We wrote a nightly reconciliation job to find them. That job was a sign the architecture was working against us.

### 5. The team scaling we planned for didn't arrive the way we expected

We did grow, but from 9 engineers to 16, not from 9 to 30. With 16 engineers and 14 services, many services had no clear owner. Some went months without a commit, so the next person who touched one had to relearn its quirks, its outdated dependencies, and its deploy process from scratch.

Microservices mostly solve an organizational problem: many teams needing to deploy independently without coordinating. We didn't have that problem. We had three teams who already talked to each other every day.

### 6. Local development got worse

Running the full product locally required Docker Compose with 14 services, several databases, a message broker, and enough RAM to make laptops struggle. Most people stopped running the full stack and developed against a shared staging environment instead, which was often broken by someone else's half-deployed change.

New hires used to ship to production in their first week. During the microservices period, that slipped to roughly their third week.

## The decision

We didn't decide this in one meeting. Over about two months, we:

1. **Wrote down the problems** with numbers wherever we had them (incident resolution time, lead time for changes, time spent on maintenance, onboarding time).
2. **Mapped which services changed together.** We looked at a year of PRs and grouped services that were modified in the same feature work. The clusters were obvious. Ten of the fourteen services almost always changed together.
3. **Asked what independent deployment had actually given us.** For most services, the honest answer was nothing. They deployed in lockstep anyway.
4. **Identified the services with a real reason to stay separate.** Two did (more on those below).

The proposal was to consolidate into a **modular monolith**: one deployable application, one primary database, and strictly enforced module boundaries inside the codebase.

## Why a *modular* monolith matters

We didn't want to recreate the tangled codebase we had started with. The original pain was real. It was caused by missing boundaries, not by having a single deployable.

So the new application is organized into modules that mirror our domains:

```
app/
  modules/
    accounts/
      public/        # the only thing other modules may import
      internal/
    billing/
      public/
      internal/
    documents/
    notifications/
    integrations/
    ...
  shared/            # small, deliberately boring utilities
```

The rules are:

- **Modules talk to each other only through their `public` interface.** A linter rule in CI enforces this, so a module importing another module's `internal` code fails the build.
- **Each module owns its tables.** All modules share one Postgres instance, but each has its own schema, and no module writes to another module's schema. Reads across modules go through the public interface, not direct queries.
- **Cross-module side effects use in-process domain events.** For example, `billing` publishes `SubscriptionChanged` and `accounts` reacts. This keeps modules decoupled without putting a network between them, and it lets us use a single database transaction where we want one.

This gives us most of the design benefits we wanted from microservices (clear ownership, explicit contracts, a codebase you can reason about one area at a time) without the operational cost. If a module ever does need to become a separate service, its boundary is already defined.

## How we migrated

We didn't do a big-bang rewrite. Feature work continued throughout, and the migration took about **five months** with two to four engineers on it at any given time.

**Step 1: Create the host application.** We started a new monolith repo with the module structure, CI, and the boundary linter, but no business logic yet.

**Step 2: Move services in, one at a time, starting with the least risky.** For each service:

1. Copy the code into its module, keeping the existing API handlers.
2. Point the remaining services at the module's endpoints in the new application instead of the old service. The network call still existed at this stage, but it now went to the monolith.
3. Migrate the data into the module's schema in the shared database, using dual writes for the higher-traffic services until the counts reconciled.
4. Replace internal HTTP calls with direct calls to the module's public interface, one call site at a time.
5. Delete the old service, its pipeline, and its infrastructure.

We started with `audit-log` and `notifications`, which were small and had few dependencies, so we could refine the process before we touched `billing`.

**Step 3: Delete the reconciliation jobs.** With billing and accounts sharing a database again, plan changes became a single transaction. The nightly reconciliation job, and the inconsistent records it kept finding, went away.

Deleting things was by far the most satisfying part of the project. In total we removed 12 CI pipelines, roughly 40 Kubernetes manifests, a service mesh configuration we had never fully understood, and about **18,000 lines** of client code, retry logic, and serialization glue.

## What we kept separate

We didn't consolidate everything. Two services stayed on their own, for specific reasons:

- **Document processing.** This handles PDF rendering and OCR. It is CPU- and memory-intensive, uses native dependencies we don't want in the main application, and has a very different scaling profile from the rest of the product. It's a worker that consumes jobs from a queue and has no synchronous callers.
- **The integrations sync runner.** This polls third-party APIs on schedules and is often slowed down by other companies' rate limits and outages. Isolating it means a misbehaving partner API can't use up the web application's connection pool.

Both have **different runtime characteristics** from the main application. That is a much better reason to run something separately than "it's a different domain."

## Results

About three months after finishing, compared with our microservices period:

| Metric | Microservices | Modular monolith |
|---|---|---|
| Deployable units | 14 | 3 |
| Median lead time (merge → production) | ~2 days | ~40 minutes |
| Median incident resolution time | ~3 hours | ~50 minutes |
| Engineering time spent on maintenance (estimated) | ~30% | ~10% |
| New hire time to first production change | ~3 weeks | 3–4 days |
| Monthly infrastructure spend | baseline | ~35% lower |

Some notes:

- The lead time improvement came mostly from no longer needing coordinated multi-repo deploys. A cross-domain feature is one PR now.
- The infrastructure savings came from removing per-service overhead: sidecars, minimum replica counts, idle databases, and load balancers. Our actual compute needs barely changed.
- CI is **not** 25 minutes again. We split the test suite by module and only run the modules affected by a change, plus a smaller set of integration tests. The median CI run is about 7 minutes.

## What got worse

To be fair to the other side:

- **The blast radius is bigger.** A memory leak in one module can affect the whole application. We handle this with good resource monitoring, fast rollbacks, and the fact that the riskiest workloads were the ones we kept separate. It's a real tradeoff, though.
- **Boundaries now depend on discipline and tooling, not the network.** The linter catches illegal imports, but it can't catch a poorly designed public interface. Design reviews matter more than they used to.
- **One dependency tree for everyone.** Upgrading a major framework version is now one large coordinated change instead of 14 small ones. Overall it's less work, but it's chunkier.
- **Scaling is coarser.** We can't scale the search module independently of billing. At our traffic levels this hasn't mattered.

## What we'd tell a team our size

1. **Start with a modular monolith.** Put real effort into module boundaries from day one, and enforce them in CI. Most of what makes microservices appealing is clear boundaries, and you can have those without a network in between.
2. **Extract a service only when you can name the specific problem it solves.** Good reasons include: different scaling or resource profile, different deploy cadence that is *actually* blocking a team, fault isolation from an unreliable dependency, or a separate team that genuinely needs autonomy. "It's a different domain" isn't enough on its own.
3. **Count the services per engineer.** If you have more services than people who can confidently operate them, you will have orphaned systems.
4. **Look at your change history.** If services almost always change together, they are one service in practice, whatever your infrastructure says.
5. **Architecture should follow your organization, not the one you hope to have.** If we grow to 100 engineers with eight independent teams, we may extract more services, and the module boundaries will make that straightforward. We'll do it when the coordination problem actually exists.

## Closing

We don't regret trying microservices. We learned a lot about our domain while drawing those boundaries, and much of that learning lives on in the module structure of the monolith. But we paid for operational complexity years before we needed it, and the main cost was time spent away from building the product.

The best architecture for a 40-person startup is the one that lets 16 engineers ship confidently and understand the system when it breaks. For us, right now, that's one well-organized application.

*If you've made a similar move, in either direction, we'd love to hear about it. And if working on a codebase you can run on your laptop sounds good to you, [we're hiring](#).*
