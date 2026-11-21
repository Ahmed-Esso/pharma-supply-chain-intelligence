# Agent Handoff Context — Pharma Supply Chain Intelligence

**Purpose:** a concise, evidence-aware context file for another agent continuing planning, documentation, implementation, or ClickUp work on this DEPI capstone.

**Last consolidated:** 4 November 2026 (Africa/Cairo). ClickUp status values below were read from the live workspace on this date; the most recent task updates shown in ClickUp are largely from 21 October 2026.

## Critical status caveat

ClickUp contains planned tasks and a small set marked `In Progress`. That is **not evidence that implementation is complete**. Do not claim that any component, source integration, RAG pipeline, UI, test, or deliverable has been built or validated unless new evidence is supplied. Treat `In Progress` as a workspace label only, and confirm progress with the assignee or artifacts before reporting it.

## Project identity and intent

- **Project:** Pharma Supply Chain Intelligence
- **Capstone type:** DEPI team project (four members)
- **Proposed title:** *Pharma Supply Chain Intelligence: A Data Engineering and RAG-Based Platform*
- **Goal:** create a source-aware platform that gathers accessible pharmaceutical supply-chain-related data, organizes and validates it, and supports analysis plus evidence-grounded document retrieval.
- **Key constraint:** public sources may not provide real-time stock, market pricing, or all recall fields. Never present unverified, sample, or synthetic values as real market data. Clearly label sample/synthetic data.

## Confirmed team ownership

| Member | Primary workstream | Main responsibility |
|---|---|---|
| Mohamed Nasr | Data ingestion & workflow orchestration | Source register, access validation, reusable Python connectors, Airflow scheduling/retries/logging, failure/rerun validation. |
| Ahmed Essam | Lakehouse & data quality | Bronze/Silver/Gold design, data dictionary, transformations, quality checks, analytics-ready tables, MVP validation. |
| Mayar Hany | Document processing & RAG | Source-document inventory, extraction with OCR fallback, chunking/embeddings, retrieval, grounded citations, RAG evaluation. |
| Rawan Husseiny | API, UI & integration | UI and applicable API endpoints, connecting system components, user-facing display, end-to-end demo/testing coordination. |

Shared responsibilities: agree component contracts and shared schemas; maintain documentation/Git standards; integration checkpoints twice weekly; review the R01–R10 risk register; integration and end-to-end testing.

## Target architecture

```text
Accessible APIs/files ──> Python ingestion ──> Airflow orchestration
                                          │
                                          v
                              Bronze (raw + provenance)
                                          │
                                          v
                     Silver (validate / standardize / deduplicate)
                                          │
                                          v
                        Gold (analytics-ready, labelled outputs)
                                          │
                                          ├──> API / UI

Source documents ──> text extraction ──> OCR only if needed
                                  ──> chunking + embeddings ──> retrieval
                                                                  │
                                                                  v
                                                    grounded answers + citations ──> UI
```

### Architectural expectations

- Use a medallion-style Lakehouse: **Bronze** preserves raw inputs and provenance; **Silver** cleans, standardizes, validates, deduplicates, and quarantines invalid/conflicting records; **Gold** exposes analysis-ready tables.
- The planning scope names Python for ingestion, Apache Airflow for orchestration, and Databricks/Delta Lake for storage/processing. These are proposed/target technologies, not proof of an existing implementation.
- Store source name and ingestion timestamp; retain raw inputs; make reruns safe and observable with logs, timeouts, retries, and failure handling.
- Data-quality checks should cover required fields, duplicate keys, valid dates, nonnegative prices, currency/unit metadata, and drug-identifying attributes (name, active ingredient, strength, dosage form, pack size).
- RAG must return traceable source support or state that information is insufficient. OCR is fallback only when normal PDF text extraction fails.
- Component contracts must specify inputs, outputs, schemas, formats, error behavior, and ownership boundaries before implementation.
- Never commit API keys, passwords, or `.env` files; keep setup reproducible with README/environment examples and meaningful commits.

## Official project milestones

These are the supplied DEPI milestones; do not substitute an unrelated project-phase document as evidence.

| Milestone | Date |
|---|---:|
| Planning and requirements | 16 Oct 2026 |
| System analysis and design | 6 Nov 2026 |
| Implementation | 30 Nov 2026 |
| Final testing, reports, and presentation | 4 Dec 2026 |

## ClickUp workspace snapshot

| Level | Name | Identifier |
|---|---|---|
| Workspace | Workspace | `1200470000003727` |
| Space | Team Space | `1200470000017801` |
| List / project board | Pharma Supply Chain Intelligence | `1200470000021512` |

The list has 29 visible tasks, all open at the time of review: 5 marked `In Progress`, 24 `To Do`, and 0 closed. This describes ClickUp state only, not actual completion.

### Workstreams and tasks

| ID | Task | Assignee(s) | Status |
|---|---|---|---|
| `123u8tync4c` | Workstream 1 — Data Ingestion & Workflow Orchestration | Mohamed | To Do |
| `123u8tync4k` | Build data source register and validate access | Mohamed | In Progress |
| `123u8tync4m` | Implement Python ingestion connectors | Mohamed | To Do |
| `123u8tync4n` | Create Airflow DAGs with retries and logging | Mohamed | To Do |
| `123u8tync4p` | Validate ingestion failures and reruns | Mohamed | To Do |
| `123u8tync4d` | Workstream 2 — Lakehouse & Data Quality | Ahmed | To Do |
| `123u8tync4q` | Define Bronze/Silver/Gold schemas and data dictionary | Ahmed, Mohamed | In Progress |
| `123u8tync4t` | Implement Bronze raw-data storage | Ahmed | To Do |
| `123u8tync4v` | Implement Silver cleaning and standardization | Ahmed | To Do |
| `123u8tync4w` | Build Gold analytics-ready tables | Ahmed | To Do |
| `123u8tync4x` | Create data-quality checks and report | Ahmed, Mohamed | To Do |
| `123u8tyngjk` | Workstream 3 — Document Processing & RAG | Mayar | To Do |
| `123u8tyngjm` | Inventory and collect source documents | Mayar | In Progress |
| `123u8tyngjn` | Implement text extraction and OCR fallback | Mayar | To Do |
| `123u8tyngjp` | Build chunking and embeddings pipeline | Mayar | To Do |
| `123u8tyngk4` | Implement retrieval, grounded answers, and citations | Mayar | To Do |
| `123u8tyngk5` | Evaluate RAG relevance and citation support | Mayar | To Do |
| `123u8tync4h` | Workstream 4 — API, UI & System Integration | Rawan | To Do |
| `123u8tync55` | Define API/UI requirements and component contracts | Rawan | To Do |
| `123u8tync57` | Build application interface | Rawan | To Do |
| `123u8tync58` | Implement API endpoints where required | Rawan | To Do |
| `123u8tync59` | Integrate ingestion, Lakehouse, RAG, and UI | All four | To Do |
| `123u8tync5p` | Run end-to-end testing and prepare demo | All four | To Do |
| `123u8tync5t` | Agree component contracts and shared schemas | All four | In Progress |
| `123u8tync5u` | Maintain project documentation and Git standards | All four | To Do |
| `123u8tync61` | Run integration checkpoints twice per week | All four | To Do |
| `123u8tync62` | Review and update risk register R01–R10 | All four | To Do |
| `123u8tync6b` | MVP acceptance review and final validation | Ahmed (task field); intended all-team validation | To Do |
| `123u8tync6d` | Confirm source-data limitations and sample-data labeling | Ahmed, Mohamed, Mayar | In Progress |

## Explicit ClickUp dependency rules

The configured directional dependencies are the following. Read `A → B` as “B waits on A.”

- Data source register/validation → Python ingestion connectors → Airflow DAGs.
- Bronze/Silver/Gold schemas and data dictionary → Bronze raw-data storage → Silver cleaning and standardization.
- Silver cleaning and standardization → Gold analytics-ready tables.
- Silver cleaning and standardization → data-quality checks and report.
- Gold analytics-ready tables → system integration.
- API/UI requirements and component contracts → system integration.
- System integration → end-to-end testing/demo → MVP acceptance review/final validation.

The RAG child tasks have planned start sequencing, but no explicit ClickUp dependency records were found in this snapshot. Do not invent dependencies; add them only after the team agrees.

## Important implementation and reporting rules

1. Validate data-source access and fields before promising any coverage.
2. Preserve provenance and historical raw data; do not destructively overwrite inputs.
3. Quarantine bad/conflicting records with reasons; do not silently drop them.
4. For RAG, ground answers in retrieved sources and expose citations. When evidence is unavailable, say so.
5. Clearly distinguish real/verified source data from samples, synthetic values, assumptions, and illustrative dashboard figures.
6. Use reproducible demo inputs and record known limitations/issues.
7. Statuses should reflect actual work begun, not calendar dates or recommendations.

## Proposal headings from the latest conversation

1. Abstract
2. Introduction
3. Problem Statement
4. Project Objectives
5. Proposed Solution
6. Project Scope
7. Literature Review
8. System Architecture
9. Methodology and Implementation Plan
10. Technologies and Tools
11. Data Sources
12. Expected Outcomes and Deliverables
13. Project Timeline
14. Team Structure and Responsibilities
15. Risks and Limitations
16. Testing and Evaluation
17. Conclusion
18. References

## Proposal-scope notes from the same context

- Suggested measurable objectives: repeatable ingestion; Bronze/Silver/Gold layers; data-quality validation; source-backed RAG; and an interface for results.
- Suggested in-scope items: Python ingestion, Airflow, Databricks/Delta Lake, medallion layers, quality validation, document processing/RAG, API/UI, and integration testing.
- Any stated problem (multiple sources, incompatible formats, missing/inconsistent data, difficult document search) is a proposed problem statement and must be checked against the actual sources selected by the team.

## Recommended handoff posture for the next agent

Use the project plan and ClickUp board as planning context, not proof of delivered work. Begin by asking for or inspecting the repository, source register, data samples, Airflow/Databricks setup, source documents, and any demo/test artifacts. Update task statuses only after confirming real work, and retain the labelling and evidence rules above in all documentation and UI copy.
