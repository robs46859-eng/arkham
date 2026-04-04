# System Contracts Document

## Purpose

This document defines the non-negotiable contracts between all services in the platform. These contracts ensure consistency, scalability, and the ability to split services into independent systems without breaking functionality.

---

## Core Principles

- All communication is schema-driven
- All data is tenant-scoped
- All outputs are traceable
- No service owns another service’s data
- Structured data is always the source of truth

---

## Global ID Format

All entities must follow:

<type>_<ulid>

Examples:
- tenant_...
- proj_...
- file_...
- elem_...
- issue_...
- wf_...

---

## Gateway Contract

### Request

{
  "tenant_id": "tenant_...",
  "project_id": "proj_...",
  "task_type": "classification | extraction | summary | workflow",
  "input": {
    "text": "...",
    "context": {},
    "references": []
  },
  "options": {
    "allow_premium": false,
    "require_schema": true
  }
}

### Response

{
  "request_id": "req_...",
  "tenant_id": "tenant_...",
  "model_used": "local | mid | premium",
  "cache_hit": true,
  "latency_ms": 0,
  "cost_estimate": 0,
  "output": {},
  "validation": {
    "passed": true,
    "errors": []
  }
}

---

## Ingestion Contract

### Input

{
  "tenant_id": "tenant_...",
  "project_id": "proj_...",
  "file_id": "file_...",
  "file_type": "ifc | pdf | schedule | markup",
  "storage_path": "..."
}

### Output

{
  "job_id": "job_...",
  "status": "queued | processing | complete | failed",
  "entities_created": 0,
  "errors": []
}

---

## Building Element Contract

{
  "element_id": "elem_...",
  "project_id": "proj_...",
  "category": "...",
  "properties": {},
  "source_file_id": "file_...",
  "created_at": "..."
}

---

## Document Chunk Contract

{
  "chunk_id": "chunk_...",
  "file_id": "file_...",
  "page": 0,
  "text": "...",
  "confidence": 0
}

---

## Issue Contract

{
  "issue_id": "issue_...",
  "project_id": "proj_...",
  "type": "...",
  "severity": "low | medium | high",
  "source_refs": [],
  "confidence": 0
}

---

## Workflow Contract

{
  "workflow_id": "wf_...",
  "type": "...",
  "status": "running | complete | failed",
  "current_step": "...",
  "checkpoint": {}
}

---

## Deliverable Contract

{
  "deliverable_id": "deliv_...",
  "project_id": "proj_...",
  "type": "...",
  "artifact_path": "...",
  "source_trace": [],
  "created_at": "..."
}

---

## Memory Contract

{
  "note_id": "mem_...",
  "tenant_id": "tenant_...",
  "project_id": "proj_...",
  "content": "...",
  "tags": [],
  "links": []
}

---

## Usage Contract

{
  "usage_id": "usage_...",
  "tenant_id": "tenant_...",
  "service": "...",
  "cost": 0,
  "timestamp": "..."
}

---

## Non-Negotiable Rules

- No unstructured responses between services
- No cross-tenant data access
- No hidden state
- All workflows must be restartable
- All outputs must be traceable

---

## Summary

This document defines the contracts that hold the system together. All services must follow these rules to maintain consistency, safety, and scalability.

