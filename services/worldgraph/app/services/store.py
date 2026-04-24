"""Worldgraph persistence helpers."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from packages.models import (
    WorldgraphEntityAliasRecord,
    WorldgraphEntityCategoryRecord,
    WorldgraphEntityProposalRecord,
    WorldgraphEntityIdentifierRecord,
    WorldgraphEntityRecord,
    WorldgraphIngestJobRecord,
    WorldgraphRawObjectRecord,
    WorldgraphRawRecordRecord,
    WorldgraphSearchDocumentRecord,
    WorldgraphTravelRawAirlineRecord,
    WorldgraphTravelRawAirportRecord,
    WorldgraphTravelRawRouteRecord,
)
from packages.schemas.worldgraph import (
    WorldgraphAlias,
    WorldgraphEntity,
    WorldgraphIdentifier,
    WorldgraphIngestJob,
)


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return base or "entity"


def _now() -> datetime:
    return datetime.utcnow()


def create_ingest_job(db: Session, namespace: str, source_name: str) -> WorldgraphIngestJobRecord:
    record = WorldgraphIngestJobRecord(
        job_id=f"wgjob_{uuid.uuid4().hex}",
        namespace=namespace,
        source_name=source_name,
        status="pending",
        stats_json={},
        error_json={},
        started_at=_now(),
        finished_at=None,
    )
    db.add(record)
    db.commit()
    return record


def set_ingest_job_running(db: Session, job_id: str) -> None:
    record = db.get(WorldgraphIngestJobRecord, job_id)
    if record is None:
        raise ValueError(f"Unknown ingest job: {job_id}")
    record.status = "running"
    record.started_at = _now()
    db.commit()


def set_ingest_job_completed(db: Session, job_id: str, *, manifest_uri: str, stats_json: dict[str, Any]) -> None:
    record = db.get(WorldgraphIngestJobRecord, job_id)
    if record is None:
        raise ValueError(f"Unknown ingest job: {job_id}")
    record.status = "complete"
    record.manifest_uri = manifest_uri
    record.stats_json = stats_json
    record.finished_at = _now()
    db.commit()


def set_ingest_job_failed(db: Session, job_id: str, *, error: str) -> None:
    record = db.get(WorldgraphIngestJobRecord, job_id)
    if record is None:
        return
    record.status = "failed"
    record.error_json = {"message": error}
    record.finished_at = _now()
    db.commit()


def list_ingest_jobs(db: Session, namespace: str, source_name: str | None = None) -> list[WorldgraphIngestJob]:
    query = db.query(WorldgraphIngestJobRecord).filter(WorldgraphIngestJobRecord.namespace == namespace)
    if source_name:
        query = query.filter(WorldgraphIngestJobRecord.source_name == source_name)
    rows = query.order_by(WorldgraphIngestJobRecord.started_at.desc()).limit(100).all()
    return [
        WorldgraphIngestJob(
            job_id=row.job_id,
            namespace=row.namespace,  # type: ignore[arg-type]
            source_name=row.source_name,
            status=row.status,  # type: ignore[arg-type]
            manifest_uri=row.manifest_uri,
            stats_json=row.stats_json or {},
            error_json=row.error_json or {},
            started_at=row.started_at,
            finished_at=row.finished_at,
        )
        for row in rows
    ]


def register_raw_object(
    db: Session,
    *,
    namespace: str,
    source_name: str,
    object_uri: str,
    checksum_sha256: str,
    content_type: str,
    metadata_json: dict[str, Any],
) -> WorldgraphRawObjectRecord:
    existing = (
        db.query(WorldgraphRawObjectRecord)
        .filter(WorldgraphRawObjectRecord.namespace == namespace)
        .filter(WorldgraphRawObjectRecord.source_name == source_name)
        .filter(WorldgraphRawObjectRecord.checksum_sha256 == checksum_sha256)
        .first()
    )
    if existing is not None:
        return existing
    record = WorldgraphRawObjectRecord(
        raw_object_id=f"wgrawobj_{uuid.uuid4().hex}",
        namespace=namespace,
        source_name=source_name,
        object_uri=object_uri,
        checksum_sha256=checksum_sha256,
        content_type=content_type,
        metadata_json=metadata_json,
        ingested_at=_now(),
    )
    db.add(record)
    db.commit()
    return record


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(str(sorted(payload.items())).encode("utf-8")).hexdigest()


def _upsert_category(db: Session, entity_id: str, category: str, confidence: float = 1.0) -> None:
    existing = (
        db.query(WorldgraphEntityCategoryRecord)
        .filter(WorldgraphEntityCategoryRecord.entity_id == entity_id)
        .filter(WorldgraphEntityCategoryRecord.category == category)
        .first()
    )
    if existing:
        existing.confidence = confidence
        return
    db.add(
        WorldgraphEntityCategoryRecord(
            entity_id=entity_id,
            category=category,
            confidence=confidence,
        )
    )


def _upsert_airport_entity(db: Session, payload: dict[str, Any], raw_record_id: str) -> WorldgraphEntityRecord:
    strong_codes = [payload.get("iata"), payload.get("icao"), payload.get("airport_id")]
    strong_codes = [c for c in strong_codes if c and c != "\\N"]

    query = db.query(WorldgraphEntityRecord).filter(WorldgraphEntityRecord.namespace == "travel").filter(
        WorldgraphEntityRecord.entity_type == "airport"
    )
    if payload.get("name"):
        query = query.filter(WorldgraphEntityRecord.display_name == payload["name"])
    existing = query.first()
    if existing is None and strong_codes:
        identifier = (
            db.query(WorldgraphEntityIdentifierRecord)
            .filter(WorldgraphEntityIdentifierRecord.namespace == "travel")
            .filter(WorldgraphEntityIdentifierRecord.scheme.in_(["iata", "icao", "openflights_airport_id"]))
            .filter(WorldgraphEntityIdentifierRecord.value.in_(strong_codes))
            .first()
        )
        if identifier:
            existing = db.get(WorldgraphEntityRecord, identifier.entity_id)

    now = _now()
    if existing is None:
        existing = WorldgraphEntityRecord(
            entity_id=f"wg_travel_{uuid.uuid4().hex}",
            namespace="travel",
            entity_type="airport",
            display_name=payload.get("name") or payload.get("airport_id") or "unknown-airport",
            canonical_slug=_slugify(payload.get("name") or payload.get("airport_id") or "airport"),
            description=f"Airport in {payload.get('city') or 'unknown city'}, {payload.get('country') or 'unknown country'}",
            status="active",
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            canonical_json=payload,
            created_at=now,
            updated_at=now,
        )
        db.add(existing)
    else:
        existing.display_name = payload.get("name") or existing.display_name
        existing.latitude = payload.get("latitude")
        existing.longitude = payload.get("longitude")
        existing.canonical_json = payload
        existing.updated_at = now

    _upsert_category(db, existing.entity_id, "airport", 1.0)
    _upsert_identifier(db, existing.entity_id, "travel", "openflights_airport_id", payload.get("airport_id"))
    _upsert_identifier(db, existing.entity_id, "travel", "iata", payload.get("iata"))
    _upsert_identifier(db, existing.entity_id, "travel", "icao", payload.get("icao"))
    _upsert_alias(db, existing.entity_id, payload.get("city"), "city", False)
    _upsert_alias(db, existing.entity_id, payload.get("country"), "country", False)
    return existing


def _upsert_airline_entity(db: Session, payload: dict[str, Any], raw_record_id: str) -> WorldgraphEntityRecord:
    _ = raw_record_id
    strong_codes = [payload.get("iata"), payload.get("icao"), payload.get("airline_id")]
    strong_codes = [c for c in strong_codes if c and c != "\\N"]

    query = db.query(WorldgraphEntityRecord).filter(WorldgraphEntityRecord.namespace == "travel").filter(
        WorldgraphEntityRecord.entity_type == "airline"
    )
    if payload.get("name"):
        query = query.filter(WorldgraphEntityRecord.display_name == payload["name"])
    existing = query.first()
    if existing is None and strong_codes:
        identifier = (
            db.query(WorldgraphEntityIdentifierRecord)
            .filter(WorldgraphEntityIdentifierRecord.namespace == "travel")
            .filter(WorldgraphEntityIdentifierRecord.scheme.in_(["iata", "icao", "openflights_airline_id"]))
            .filter(WorldgraphEntityIdentifierRecord.value.in_(strong_codes))
            .first()
        )
        if identifier:
            existing = db.get(WorldgraphEntityRecord, identifier.entity_id)

    now = _now()
    if existing is None:
        existing = WorldgraphEntityRecord(
            entity_id=f"wg_travel_{uuid.uuid4().hex}",
            namespace="travel",
            entity_type="airline",
            display_name=payload.get("name") or payload.get("airline_id") or "unknown-airline",
            canonical_slug=_slugify(payload.get("name") or payload.get("airline_id") or "airline"),
            description=f"Airline based in {payload.get('country') or 'unknown country'}",
            status="active",
            canonical_json=payload,
            created_at=now,
            updated_at=now,
        )
        db.add(existing)
    else:
        existing.display_name = payload.get("name") or existing.display_name
        existing.canonical_json = payload
        existing.updated_at = now
    _upsert_category(db, existing.entity_id, "airline", 1.0)
    _upsert_identifier(db, existing.entity_id, "travel", "openflights_airline_id", payload.get("airline_id"))
    _upsert_identifier(db, existing.entity_id, "travel", "iata", payload.get("iata"))
    _upsert_identifier(db, existing.entity_id, "travel", "icao", payload.get("icao"))
    _upsert_alias(db, existing.entity_id, payload.get("alias"), "alias", False)
    return existing


def _upsert_route_entity(db: Session, payload: dict[str, Any], raw_record_id: str) -> WorldgraphEntityRecord:
    _ = raw_record_id
    route_key = payload.get("route_key") or f"{payload.get('airline_code')}:{payload.get('source_airport')}:{payload.get('destination_airport')}"
    identifier = (
        db.query(WorldgraphEntityIdentifierRecord)
        .filter(WorldgraphEntityIdentifierRecord.namespace == "travel")
        .filter(WorldgraphEntityIdentifierRecord.scheme == "route_key")
        .filter(WorldgraphEntityIdentifierRecord.value == route_key)
        .first()
    )
    existing = db.get(WorldgraphEntityRecord, identifier.entity_id) if identifier else None
    now = _now()
    display_name = f"{payload.get('source_airport') or 'UNK'}->{payload.get('destination_airport') or 'UNK'}"
    if existing is None:
        existing = WorldgraphEntityRecord(
            entity_id=f"wg_travel_{uuid.uuid4().hex}",
            namespace="travel",
            entity_type="route",
            display_name=display_name,
            canonical_slug=_slugify(route_key),
            description=f"Route operated by {payload.get('airline_code') or 'unknown airline'}",
            status="active",
            canonical_json=payload,
            created_at=now,
            updated_at=now,
        )
        db.add(existing)
    else:
        existing.display_name = display_name
        existing.canonical_json = payload
        existing.updated_at = now
    _upsert_category(db, existing.entity_id, "route", 1.0)
    _upsert_identifier(db, existing.entity_id, "travel", "route_key", route_key)
    _upsert_alias(db, existing.entity_id, payload.get("airline_code"), "airline_code", False)
    return existing


def _queue_identifier_collision_review(
    db: Session,
    *,
    namespace: str,
    scheme: str,
    value: str,
    existing_entity_id: str,
    incoming_entity_id: str,
) -> None:
    fingerprint = hashlib.sha256(
        f"{namespace}:{scheme}:{value}:{existing_entity_id}:{incoming_entity_id}".encode("utf-8")
    ).hexdigest()
    proposal_id = f"wgprop_coll_{fingerprint[:24]}"
    existing = db.get(WorldgraphEntityProposalRecord, proposal_id)
    if existing is not None:
        return
    db.add(
        WorldgraphEntityProposalRecord(
            proposal_id=proposal_id,
            namespace=namespace,
            proposal_type="identifier_collision",
            status="pending",
            confidence=0.25,
            reasoning=(
                f"Identifier collision for {scheme}={value}. "
                f"Existing entity={existing_entity_id}, incoming entity={incoming_entity_id}. "
                "Manual review required before reassignment."
            ),
            draft_entity_json={
                "scheme": scheme,
                "value": value,
                "existing_entity_id": existing_entity_id,
                "incoming_entity_id": incoming_entity_id,
            },
            dedupe_candidates_json=[
                {"entity_id": existing_entity_id, "risk": 1.0},
                {"entity_id": incoming_entity_id, "risk": 1.0},
            ],
            created_by_job_id="trusted_seed_ingest",
            created_at=_now(),
        )
    )


def _upsert_identifier(db: Session, entity_id: str, namespace: str, scheme: str, value: str | None) -> None:
    if not value or value == "\\N":
        return
    existing = (
        db.query(WorldgraphEntityIdentifierRecord)
        .filter(WorldgraphEntityIdentifierRecord.namespace == namespace)
        .filter(WorldgraphEntityIdentifierRecord.scheme == scheme)
        .filter(WorldgraphEntityIdentifierRecord.value == value)
        .first()
    )
    if existing:
        if existing.entity_id != entity_id:
            _queue_identifier_collision_review(
                db,
                namespace=namespace,
                scheme=scheme,
                value=value,
                existing_entity_id=existing.entity_id,
                incoming_entity_id=entity_id,
            )
        return
    db.add(
        WorldgraphEntityIdentifierRecord(
            identifier_id=f"wgid_{uuid.uuid4().hex}",
            entity_id=entity_id,
            namespace=namespace,
            scheme=scheme,
            value=value,
        )
    )


def _upsert_alias(db: Session, entity_id: str, alias: str | None, alias_type: str, is_primary: bool) -> None:
    if not alias or alias == "\\N":
        return
    existing = (
        db.query(WorldgraphEntityAliasRecord)
        .filter(WorldgraphEntityAliasRecord.entity_id == entity_id)
        .filter(WorldgraphEntityAliasRecord.alias == alias)
        .first()
    )
    if existing:
        return
    db.add(
        WorldgraphEntityAliasRecord(
            alias_id=f"wgalias_{uuid.uuid4().hex}",
            entity_id=entity_id,
            alias=alias,
            alias_type=alias_type,
            is_primary=is_primary,
        )
    )


def stage_openflights_airport(
    db: Session,
    *,
    job_id: str,
    raw_object_id: str,
    payload: dict[str, Any],
) -> None:
    source_primary_key = str(payload.get("airport_id") or "")
    payload_hash = _hash_payload(payload)
    existing_raw = (
        db.query(WorldgraphRawRecordRecord)
        .filter(WorldgraphRawRecordRecord.namespace == "travel")
        .filter(WorldgraphRawRecordRecord.source_name == "openflights")
        .filter(WorldgraphRawRecordRecord.source_primary_key == source_primary_key)
        .filter(WorldgraphRawRecordRecord.payload_hash == payload_hash)
        .first()
    )
    record_id = existing_raw.raw_record_id if existing_raw else f"wgrawrec_{uuid.uuid4().hex}"
    if existing_raw is None:
        db.add(
            WorldgraphRawRecordRecord(
                raw_record_id=record_id,
                job_id=job_id,
                namespace="travel",
                source_name="openflights",
                source_primary_key=source_primary_key or record_id,
                raw_object_id=raw_object_id,
                payload_json=payload,
                payload_hash=payload_hash,
                schema_version="travel-airport-v1",
                created_at=_now(),
            )
        )
    existing_typed = db.get(WorldgraphTravelRawAirportRecord, record_id)
    if existing_typed is None:
        db.add(
            WorldgraphTravelRawAirportRecord(
                raw_record_id=record_id,
                airport_id=str(payload.get("airport_id") or ""),
                name=str(payload.get("name") or "unknown-airport"),
                city=payload.get("city"),
                country=payload.get("country"),
                iata=payload.get("iata"),
                icao=payload.get("icao"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                payload_json=payload,
                ingested_at=_now(),
            )
        )
    _upsert_airport_entity(db, payload, record_id)


def stage_openflights_airline(
    db: Session,
    *,
    job_id: str,
    raw_object_id: str,
    payload: dict[str, Any],
) -> None:
    source_primary_key = str(payload.get("airline_id") or "")
    payload_hash = _hash_payload(payload)
    existing_raw = (
        db.query(WorldgraphRawRecordRecord)
        .filter(WorldgraphRawRecordRecord.namespace == "travel")
        .filter(WorldgraphRawRecordRecord.source_name == "openflights")
        .filter(WorldgraphRawRecordRecord.source_primary_key == source_primary_key)
        .filter(WorldgraphRawRecordRecord.payload_hash == payload_hash)
        .first()
    )
    record_id = existing_raw.raw_record_id if existing_raw else f"wgrawrec_{uuid.uuid4().hex}"
    if existing_raw is None:
        db.add(
            WorldgraphRawRecordRecord(
                raw_record_id=record_id,
                job_id=job_id,
                namespace="travel",
                source_name="openflights",
                source_primary_key=source_primary_key or record_id,
                raw_object_id=raw_object_id,
                payload_json=payload,
                payload_hash=payload_hash,
                schema_version="travel-airline-v1",
                created_at=_now(),
            )
        )
    existing_typed = db.get(WorldgraphTravelRawAirlineRecord, record_id)
    if existing_typed is None:
        db.add(
            WorldgraphTravelRawAirlineRecord(
                raw_record_id=record_id,
                airline_id=str(payload.get("airline_id") or ""),
                name=str(payload.get("name") or "unknown-airline"),
                alias=payload.get("alias"),
                iata=payload.get("iata"),
                icao=payload.get("icao"),
                callsign=payload.get("callsign"),
                country=payload.get("country"),
                payload_json=payload,
                ingested_at=_now(),
            )
        )
    _upsert_airline_entity(db, payload, record_id)


def stage_openflights_route(
    db: Session,
    *,
    job_id: str,
    raw_object_id: str,
    payload: dict[str, Any],
) -> None:
    route_key = payload.get("route_key") or f"{payload.get('airline_code')}:{payload.get('source_airport')}:{payload.get('destination_airport')}"
    payload_hash = _hash_payload(payload)
    existing_raw = (
        db.query(WorldgraphRawRecordRecord)
        .filter(WorldgraphRawRecordRecord.namespace == "travel")
        .filter(WorldgraphRawRecordRecord.source_name == "openflights")
        .filter(WorldgraphRawRecordRecord.source_primary_key == str(route_key))
        .filter(WorldgraphRawRecordRecord.payload_hash == payload_hash)
        .first()
    )
    record_id = existing_raw.raw_record_id if existing_raw else f"wgrawrec_{uuid.uuid4().hex}"
    if existing_raw is None:
        db.add(
            WorldgraphRawRecordRecord(
                raw_record_id=record_id,
                job_id=job_id,
                namespace="travel",
                source_name="openflights",
                source_primary_key=str(route_key),
                raw_object_id=raw_object_id,
                payload_json=payload,
                payload_hash=payload_hash,
                schema_version="travel-route-v1",
                created_at=_now(),
            )
        )
    existing_typed = db.get(WorldgraphTravelRawRouteRecord, record_id)
    if existing_typed is None:
        db.add(
            WorldgraphTravelRawRouteRecord(
                raw_record_id=record_id,
                route_key=str(route_key),
                airline_code=payload.get("airline_code"),
                source_airport=payload.get("source_airport"),
                destination_airport=payload.get("destination_airport"),
                stops=payload.get("stops"),
                payload_json=payload,
                ingested_at=_now(),
            )
        )
    _upsert_route_entity(db, payload, record_id)


def list_entities(db: Session, namespace: str, query_text: str | None, entity_type: str | None, limit: int) -> list[WorldgraphEntity]:
    query = db.query(WorldgraphEntityRecord).filter(WorldgraphEntityRecord.namespace == namespace)
    if entity_type:
        query = query.filter(WorldgraphEntityRecord.entity_type == entity_type)
    if query_text:
        pattern = f"%{query_text}%"
        document_entity_ids = db.query(WorldgraphSearchDocumentRecord.entity_id).filter(
            WorldgraphSearchDocumentRecord.search_text.ilike(pattern)
        )
        query = query.filter(WorldgraphEntityRecord.entity_id.in_(document_entity_ids))
    rows = query.order_by(WorldgraphEntityRecord.updated_at.desc()).limit(limit).all()
    return [to_schema_entity(db, row) for row in rows]


def get_entity(db: Session, namespace: str, entity_id: str) -> WorldgraphEntity | None:
    row = (
        db.query(WorldgraphEntityRecord)
        .filter(WorldgraphEntityRecord.namespace == namespace)
        .filter(WorldgraphEntityRecord.entity_id == entity_id)
        .first()
    )
    if row is None:
        return None
    return to_schema_entity(db, row)


def to_schema_entity(db: Session, row: WorldgraphEntityRecord) -> WorldgraphEntity:
    aliases = (
        db.query(WorldgraphEntityAliasRecord).filter(WorldgraphEntityAliasRecord.entity_id == row.entity_id).all()
    )
    identifiers = (
        db.query(WorldgraphEntityIdentifierRecord)
        .filter(WorldgraphEntityIdentifierRecord.entity_id == row.entity_id)
        .all()
    )
    categories = (
        db.query(WorldgraphEntityCategoryRecord).filter(WorldgraphEntityCategoryRecord.entity_id == row.entity_id).all()
    )
    return WorldgraphEntity(
        entity_id=row.entity_id,
        namespace=row.namespace,  # type: ignore[arg-type]
        entity_type=row.entity_type,  # type: ignore[arg-type]
        display_name=row.display_name,
        description=row.description,
        canonical_slug=row.canonical_slug,
        aliases=[
            WorldgraphAlias(
                alias=a.alias,
                language_code=a.language_code,
                alias_type=a.alias_type,
                is_primary=a.is_primary,
            )
            for a in aliases
        ],
        identifiers=[WorldgraphIdentifier(scheme=i.scheme, value=i.value) for i in identifiers],
        categories=[c.category for c in categories],
        canonical_json=row.canonical_json or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def refresh_search_documents(db: Session, namespace: str) -> int:
    entities = db.query(WorldgraphEntityRecord).filter(WorldgraphEntityRecord.namespace == namespace).all()
    count = 0
    for entity in entities:
        aliases = (
            db.query(WorldgraphEntityAliasRecord.alias)
            .filter(WorldgraphEntityAliasRecord.entity_id == entity.entity_id)
            .all()
        )
        alias_text = " ".join([a[0] for a in aliases])
        search_text = " ".join(
            [
                entity.display_name or "",
                entity.description or "",
                alias_text,
                str(entity.canonical_json or ""),
            ]
        )
        document = db.get(WorldgraphSearchDocumentRecord, entity.entity_id)
        if document is None:
            document = WorldgraphSearchDocumentRecord(
                entity_id=entity.entity_id,
                search_text=search_text,
                updated_at=_now(),
            )
            db.add(document)
        else:
            document.search_text = search_text
            document.updated_at = _now()
        count += 1
    db.commit()
    return count

