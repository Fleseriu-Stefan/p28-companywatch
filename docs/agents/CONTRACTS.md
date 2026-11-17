# Contracts — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> Promises across a boundary. **Provided:** this repo owns the contract; the text
> lives here only. **Consumed:** a link to the provider's entry plus the fields this
> repo relies on. **External:** what we rely on from a third-party service.
> Changing a provided contract is a PROPOSAL (AGENTS.md → The gate) and the plan
> lists the consumers' files too. Status: `approved` · `proposed` · `superseded-by`.
<!-- graffino-agentic:end -->

## Index
- C-001 · Health and API documentation · provided

---

## Provided

### C-001 · Health and API documentation
- **Status:** approved
- **Date:** 2026-11-17
- **Interface:** `GET /health/live` returns HTTP 200 with `{"status":"ok"}` when the API process responds, independently of database availability. `GET /health/ready` returns HTTP 200 with `{"status":"ready"}` only when MySQL responds and the migration revision matches the application head; otherwise it returns HTTP 503 with `{"status":"not_ready"}`. Database checks have finite timeouts. Responses expose no SQL errors or connection credentials. `/openapi.json` and `/docs` provide the API contract and interactive documentation.
- **Consumers:** `compose.yaml` API healthcheck; `backend/tests/test_health.py`; `backend/tests/test_database.py`; `scripts/verify.py`. No frontend API consumer exists in M1.
- **Evidence:** User explicitly approved C-001 in the M1 plan on 2026-11-17.
- **Confirmed:** 2026-11-17

## Consumed
None identified; M1 has no consumed application contracts.

## External
None identified; no service integration is configured.
