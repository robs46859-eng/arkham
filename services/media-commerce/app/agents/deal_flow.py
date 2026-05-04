"""
DealFlow™ Agent

Autonomous lead-to-revenue conversion. Manages lead scoring, qualification,
proposal generation, negotiation, and cross-vertical routing.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)


SUPPORTED_VERTICALS = ("studio", "ecom", "saas", "staffing", "media")

# Keep routing aligned with the shared horizontal model instead of inventing
# vertical-specific schemas inside the agent.
VERTICAL_BASE_SCORES = {
    "studio": 10,
    "ecom": 12,
    "saas": 14,
    "staffing": 12,
    "media": 11,
}

VERTICAL_SIGNAL_WEIGHTS = {
    "studio": {
        "brand": 12,
        "creative": 18,
        "design": 16,
        "website redesign": 20,
        "landing page": 15,
        "video production": 22,
        "content production": 18,
        "campaign launch": 16,
    },
    "ecom": {
        "shopify": 24,
        "cart": 18,
        "checkout": 20,
        "product feed": 18,
        "sku": 16,
        "inventory": 14,
        "merch": 16,
        "subscription box": 18,
        "conversion rate": 14,
        "abandoned cart": 24,
    },
    "saas": {
        "demo": 20,
        "trial": 18,
        "api": 18,
        "integration": 20,
        "workflow automation": 22,
        "seat license": 16,
        "onboarding": 14,
        "crm sync": 18,
        "retention": 14,
        "mrr": 16,
    },
    "staffing": {
        "staffing": 24,
        "recruiting": 18,
        "recruitment": 18,
        "candidate": 16,
        "placement": 18,
        "fill shifts": 22,
        "clinician": 24,
        "nurse": 24,
        "locum": 22,
        "credentialing": 20,
        "talent pipeline": 18,
    },
    "media": {
        "affiliate": 22,
        "publisher": 20,
        "newsletter": 18,
        "sponsorship": 18,
        "audience growth": 20,
        "programmatic seo": 18,
        "ad inventory": 18,
        "cpm": 18,
        "epc": 22,
        "content monetization": 22,
    },
}

HIGH_INTENT_PATTERNS = (
    "pricing",
    "proposal",
    "quote",
    "demo",
    "trial",
    "buy",
    "purchase",
    "sign up",
    "ready to hire",
    "need this month",
    "urgent",
)


class DealFlowAgent:
    """
    DealFlow™ Agent - Lead-to-Revenue Conversion
    
    Capabilities:
    - Lead scoring and qualification
    - Cross-vertical lead routing (Scenario 5)
    - Proposal generation
    - Cold email and sequences
    - Sales enablement
    """
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url
        
    async def score_lead(
        self,
        tenant_id: str,
        lead_id: str,
        vertical: str,
    ) -> Dict[str, Any]:
        """
        Score lead based on fit and intent signals
        
        Args:
            tenant_id: Tenant identifier
            lead_id: Lead identifier
            vertical: Business vertical
            
        Returns:
            Lead score (0-100) and scoring factors
        """
        result = {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "vertical": vertical,
            "score": 0,
            "factors": [],
        }
        
        # In production, would run customer-research skill
        logger.info(f"Lead scored: {lead_id} → {result['score']}")
        return result
    
    async def route_lead(
        self,
        tenant_id: str,
        lead_id: str,
        intent_signals: List[str],
    ) -> Dict[str, Any]:
        """
        Route lead to highest-LTV vertical (Scenario 5)
        
        Args:
            tenant_id: Tenant identifier
            lead_id: Lead identifier
            intent_signals: Detected intent signals
            
        Returns:
            Routing decision with rationale
        """
        normalized_signals = self._normalize_signals(intent_signals)
        if not normalized_signals:
            raise ValueError("intent_signals must include at least one non-empty signal")

        scores_by_vertical = {
            vertical: float(base_score)
            for vertical, base_score in VERTICAL_BASE_SCORES.items()
        }
        matched_signals_by_vertical = {vertical: [] for vertical in SUPPORTED_VERTICALS}

        for signal in normalized_signals:
            for vertical, weighted_patterns in VERTICAL_SIGNAL_WEIGHTS.items():
                for pattern, weight in weighted_patterns.items():
                    if self._pattern_matches(signal, pattern):
                        scores_by_vertical[vertical] += weight
                        matched_signals_by_vertical[vertical].append(pattern)

        ranked_verticals = sorted(
            scores_by_vertical.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        routed_vertical, top_score = ranked_verticals[0]
        second_score = ranked_verticals[1][1] if len(ranked_verticals) > 1 else 0.0

        unique_matches = sorted(set(matched_signals_by_vertical[routed_vertical]))
        high_intent_count = self._count_high_intent_signals(normalized_signals)
        confidence = self._calculate_confidence(
            top_score=top_score,
            second_score=second_score,
            matched_signal_count=len(unique_matches),
            high_intent_count=high_intent_count,
        )
        requires_review = confidence < 0.55 or not unique_matches
        lead_stage = self._determine_lead_stage(
            confidence=confidence,
            high_intent_count=high_intent_count,
            requires_review=requires_review,
        )

        result = {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "routed_vertical": routed_vertical,
            "scores_by_vertical": {
                vertical: round(score, 2)
                for vertical, score in scores_by_vertical.items()
            },
            "matched_signals": {
                vertical: sorted(set(matches))
                for vertical, matches in matched_signals_by_vertical.items()
                if matches
            },
            "normalized_signals": normalized_signals,
            "confidence": round(confidence, 2),
            "requires_review": requires_review,
            "lead_stage": lead_stage,
            "next_action": "human_review" if requires_review else "route_to_vertical_queue",
            "rationale": self._build_rationale(
                routed_vertical=routed_vertical,
                unique_matches=unique_matches,
                confidence=confidence,
                requires_review=requires_review,
                second_best=ranked_verticals[1][0] if len(ranked_verticals) > 1 else None,
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Lead routed: {lead_id} → {result['routed_vertical']}")
        return result
    
    async def generate_proposal(
        self,
        tenant_id: str,
        deal_id: str,
        margin_target: float = 0.23,
    ) -> Dict[str, Any]:
        """
        Generate proposal within pricing guardrails
        
        Args:
            tenant_id: Tenant identifier
            deal_id: Deal identifier
            margin_target: Minimum margin target (23%)
            
        Returns:
            Proposal content and margin validation
        """
        result = {
            "tenant_id": tenant_id,
            "deal_id": deal_id,
            "proposal": {},
            "margin_validated": False,
            "requires_approval": False,
        }
        
        # In production, would run pricing-strategy + sales-enablement
        logger.info(f"Proposal generated for {deal_id}")
        return result
    
    async def send_cold_email(
        self,
        tenant_id: str,
        lead_id: str,
        template: str = None,
    ) -> Dict[str, Any]:
        """
        Send cold email using cold-email skill
        
        Args:
            tenant_id: Tenant identifier
            lead_id: Lead identifier
            template: Optional email template
            
        Returns:
            Email send status
        """
        result = {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "sent": True,
            "template_used": template or "default",
        }
        
        logger.info(f"Cold email sent to lead {lead_id}")
        return result
    
    async def create_email_sequence(
        self,
        tenant_id: str,
        lead_id: str,
        sequence_type: str,
    ) -> Dict[str, Any]:
        """
        Create email sequence using email-sequence skill
        
        Args:
            tenant_id: Tenant identifier
            lead_id: Lead identifier
            sequence_type: follow_up, nurture, reactivation
            
        Returns:
            Sequence creation status
        """
        result = {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "sequence_type": sequence_type,
            "emails_created": 0,
        }
        
        logger.info(f"Email sequence created: {sequence_type} for {lead_id}")
        return result
    
    async def handle_objection(
        self,
        tenant_id: str,
        deal_id: str,
        objection: str,
    ) -> Dict[str, Any]:
        """
        Handle sales objection using sales-enablement skill
        
        Args:
            tenant_id: Tenant identifier
            deal_id: Deal identifier
            objection: Objection text
            
        Returns:
            Objection handling response
        """
        result = {
            "tenant_id": tenant_id,
            "deal_id": deal_id,
            "objection": objection,
            "response": "",
            "resources": [],
        }
        
        logger.info(f"Objection handled for {deal_id}")
        return result

    def _normalize_signals(self, intent_signals: Optional[List[str]]) -> List[str]:
        normalized = []
        for signal in intent_signals or []:
            cleaned = re.sub(r"\s+", " ", signal.strip().lower())
            if cleaned:
                normalized.append(cleaned)
        return normalized

    def _pattern_matches(self, signal: str, pattern: str) -> bool:
        return pattern in signal or signal in pattern

    def _count_high_intent_signals(self, normalized_signals: List[str]) -> int:
        count = 0
        for signal in normalized_signals:
            if any(pattern in signal for pattern in HIGH_INTENT_PATTERNS):
                count += 1
        return count

    def _calculate_confidence(
        self,
        top_score: float,
        second_score: float,
        matched_signal_count: int,
        high_intent_count: int,
    ) -> float:
        gap_component = max(0.0, min(0.6, (top_score - second_score) / 40))
        evidence_component = min(0.25, matched_signal_count * 0.08)
        intent_component = min(0.15, high_intent_count * 0.075)
        return min(0.99, 0.2 + gap_component + evidence_component + intent_component)

    def _determine_lead_stage(
        self,
        confidence: float,
        high_intent_count: int,
        requires_review: bool,
    ) -> str:
        if requires_review:
            return "review"
        if confidence >= 0.8 and high_intent_count >= 1:
            return "sql"
        if confidence >= 0.6:
            return "mql"
        return "nurture"

    def _build_rationale(
        self,
        routed_vertical: str,
        unique_matches: List[str],
        confidence: float,
        requires_review: bool,
        second_best: Optional[str],
    ) -> str:
        if unique_matches:
            match_summary = ", ".join(unique_matches[:4])
            rationale = (
                f"Routed to {routed_vertical} because the lead signals aligned with "
                f"{match_summary}."
            )
        else:
            rationale = (
                f"Routed to {routed_vertical} using only baseline vertical priority because "
                "no strong signal-to-vertical match was found."
            )

        if requires_review:
            rationale += (
                f" Confidence is {confidence:.2f}, so the lead should be reviewed before "
                f"handoff. Second-best match was {second_best}."
            )
        else:
            rationale += f" Confidence is {confidence:.2f}, which is high enough for direct handoff."
        return rationale
