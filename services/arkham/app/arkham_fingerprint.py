"""Stylometric fingerprinting for AI persona attribution and drift detection."""
from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from datetime import datetime
from statistics import mean, stdev
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from packages.models.sidecar import SidecarFingerprint

VECTOR_DIM = 20

_HEDGE_WORDS = frozenset(
    "perhaps maybe might could seems appears likely possibly arguably often "
    "sometimes generally typically usually presumably".split()
)
_CERTAINTY_WORDS = frozenset(
    "definitely clearly certainly obviously always never absolutely undoubtedly "
    "precisely exactly inevitably".split()
)
_FUNCTION_WORDS = frozenset(
    "the a an in on at to for of with by that this these those it its".split()
)
_CONJUNCTIONS = frozenset("and but or yet so nor for".split())
_PASSIVE_RE = re.compile(r"\b(?:is|are|was|were|been|being)\s+\w+ed\b", re.I)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s]


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b[a-zA-Z]+\b", text.lower())


def extract_vector(texts: list[str]) -> list[float]:
    """Extract a 20-dim normalized stylometric vector from a corpus."""
    if not texts:
        return [0.0] * VECTOR_DIM

    all_sents: list[str] = []
    all_words: list[str] = []
    joined = " ".join(texts)

    for t in texts:
        all_sents.extend(_sentences(t))
        all_words.extend(_tokens(t))

    if not all_sents:
        return [0.0] * VECTOR_DIM

    n_sents = len(all_sents)
    n_words = len(all_words)

    sent_lens = [len(_tokens(s)) for s in all_sents]
    m_sent = mean(sent_lens)
    s_sent = stdev(sent_lens) / (m_sent + 1) if len(sent_lens) > 1 else 0.0

    word_lens = [len(w) for w in all_words if w]
    m_word = (mean(word_lens) / 10) if word_lens else 0.0  # normalize: 10-char word = 1.0

    unique = set(all_words)
    ttr = len(unique) / (n_words + 1)

    counts = Counter(all_words)
    hapax = sum(1 for c in counts.values() if c == 1)
    hapax_ratio = hapax / (len(unique) + 1)

    def _rate(raw: float, scale: float = 5.0) -> float:
        return min(raw / (n_sents + 1) / scale, 1.0)

    comma_rate = _rate(joined.count(","), 1.0)
    semi_rate = _rate(joined.count(";"), 0.4)
    q_rate = sum(1 for s in all_sents if "?" in s) / n_sents
    ex_rate = sum(1 for s in all_sents if "!" in s) / n_sents
    ell_rate = _rate(joined.count("..."), 0.4)

    hedge_rate = _rate(sum(1 for w in all_words if w in _HEDGE_WORDS), 0.6)
    cert_rate = _rate(sum(1 for w in all_words if w in _CERTAINTY_WORDS), 0.6)
    fp_rate = _rate(sum(1 for w in all_words if w in ("i", "me", "my", "mine", "myself")), 0.6)

    passive_rate = _rate(len(_PASSIVE_RE.findall(joined)), 0.6)

    list_markers = sum(1 for line in joined.split("\n") if re.match(r"^\s*[-*•\d+.]\s", line))
    list_rate = _rate(list_markers, 1.0)

    paras = max(1, len([p for p in joined.split("\n\n") if p.strip()]))
    para_density = min(paras / (len(joined) / 1000 + 1) / 10, 1.0)

    code_rate = min(joined.count("```") / (len(joined) / 1000 + 1) / 5, 1.0)

    avg_len = len(joined) / len(texts)
    len_norm = min(math.log10(avg_len + 1) / 4, 1.0)  # log10(10000) = 4.0

    fw_density = sum(1 for w in all_words if w in _FUNCTION_WORDS) / (n_words + 1)

    conj_rate = _rate(sum(1 for w in all_words if w in _CONJUNCTIONS), 0.6)

    return [
        min(m_sent / 50, 1.0),
        min(s_sent, 1.0),
        min(m_word, 1.0),
        ttr,
        hapax_ratio,
        comma_rate,
        semi_rate,
        q_rate,
        ex_rate,
        ell_rate,
        hedge_rate,
        cert_rate,
        fp_rate,
        passive_rate,
        list_rate,
        para_density,
        code_rate,
        len_norm,
        fw_density,
        conj_rate,
    ]


def cosine_distance(v1: list[float], v2: list[float]) -> float:
    """Cosine distance: 0.0 = identical, 1.0 = maximally different."""
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 < 1e-10 or mag2 < 1e-10:
        return 1.0
    return 1.0 - (dot / (mag1 * mag2))


def build_fingerprint(
    persona_id: str,
    tenant_id: str,
    checkpoint: str,
    corpus: list[str],
    db: "Session",
    *,
    request_id: str | None = None,
) -> SidecarFingerprint:
    """Extract stylometric vector from corpus and persist it."""
    vector = extract_vector(corpus)
    fp = SidecarFingerprint(
        id=f"fp_{uuid.uuid4().hex}",
        persona_id=persona_id,
        tenant_id=tenant_id,
        checkpoint=checkpoint,
        vector=vector,
        fp_metadata={
            "corpus_size": len(corpus),
            "total_chars": sum(len(t) for t in corpus),
            "request_id": request_id,
        },
        created_at=datetime.utcnow(),
    )
    db.add(fp)
    db.flush()
    return fp


def get_intake_fingerprint(persona_id: str, db: "Session") -> SidecarFingerprint | None:
    return (
        db.query(SidecarFingerprint)
        .filter(
            SidecarFingerprint.persona_id == persona_id,
            SidecarFingerprint.checkpoint == "intake",
        )
        .order_by(SidecarFingerprint.created_at.asc())
        .first()
    )


def find_closest(
    vector: list[float],
    db: "Session",
    *,
    checkpoint_filter: str = "yard",
) -> tuple[SidecarFingerprint | None, float]:
    """Return the closest fingerprint in the DB and its cosine distance."""
    candidates = (
        db.query(SidecarFingerprint)
        .filter(SidecarFingerprint.checkpoint == checkpoint_filter)
        .all()
    )
    if not candidates:
        return None, 1.0

    best_fp = min(candidates, key=lambda fp: cosine_distance(vector, fp.vector))
    best_dist = cosine_distance(vector, best_fp.vector)
    return best_fp, best_dist
