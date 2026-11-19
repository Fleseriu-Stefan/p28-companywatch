# CONTEXT — p28-companywatch vocabulary

<!-- graffino-agentic:begin v1 -->
> The approved terms for this project. Use each term exactly as defined, in the part
> of speech given. Never swap in a synonym; never use a word on an _Avoid_ line.
<!-- graffino-agentic:end -->

**Application server** (noun) — A database, API server or web server used by the application.
_Avoid_: none specified.

**Knowledge ledger** (noun) — The decisions, patterns, contracts and open questions under `docs/agents/`.
_Avoid_: none specified.

**EUID** (noun) — The ONRC source identifier used as a candidate natural key for
M2. Missing, inconsistent or duplicate identifiers are quarantined under D-007.
_Avoid_: treating CUI as an interchangeable identity key.

**ONRC edition** (noun) — A dated export identified by its edition date and source resource.
_Avoid_: treating edition date as publication date in CompanyWatch.

**Dataset version** (noun) — An immutable set of prepared rows identified by source resource, input kind, content hash and transformation profile.
_Avoid_: treating an ingestion attempt as a new dataset version.

**Published snapshot** (noun) — A validated dataset version made available by explicit approval and publication. Older published snapshots remain queryable.
_Avoid_: referring to staging as a published snapshot.

**Observed state** (noun) — Company information present in the latest eligible published ONRC edition on or before a requested date.
_Avoid_: exact legal state, when the evidence is a snapshot.

**Validity interval** (noun) — The range of dates for which an observed state answers historical queries under D-010.
_Avoid_: exact real-world change interval.

**Quarantined row** (noun) — A row withheld because validation failed or classification was uncertain. Policy exclusions are counted separately.
_Avoid_: merging quarantined and intentionally excluded rows into one count.

**Canonical mapping** (noun) — The explicit correspondence between a version's source schema and CompanyWatch's retained fields.
_Avoid_: treating a schema hash as a canonical mapping.

**Curator** (noun) — An authenticated operator who reviews ingestion, resolves and approves mappings, and publishes validated editions.
_Avoid_: using curator and administrator interchangeably.

**Saved visualization** (noun) — A persistent chart configuration and filters tied to exact published version IDs and accessible through a stable URL.
_Avoid_: a live view that automatically switches editions after publication.

The confirmed project purpose is ETL + API + Dashboard (D-005 and D-009). See
[requirements and roadmap](docs/P28-REQUIREMENTS.md) and
[open questions](docs/agents/OPEN-QUESTIONS.md) for outstanding evidence.
