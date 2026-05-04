"""
MediationAgent

Acts as compound memory between ContentEngine and ChiefPulse.
Monitors content approval/rejection patterns and learns to prevent
low-quality content from being created in the first place.

Key capabilities:
- Track content approval/rejection decisions
- Learn patterns from ChiefPulse signals
- Score content quality before generation
- Block low-quality content proactively
- Provide feedback to ContentEngine for improvement
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


class MediationAgent:
    """
    MediationAgent - Content Quality Gatekeeper

    Sits between ContentEngine and ChiefPulse to:
    1. Learn from approval/rejection patterns
    2. Predict content quality before generation
    3. Block low-quality content proactively
    4. Provide feedback loops for continuous improvement
    """

    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url
        self._approval_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._rejection_patterns: Dict[str, int] = defaultdict(int)
        self._quality_scores: Dict[str, float] = {}
        self._topic_performance: Dict[str, Dict[str, Any]] = {}

    async def record_content_decision(
        self,
        tenant_id: str,
        content_id: str,
        decision: str,  # "approved", "rejected", "modified"
        decision_reason: str = None,
        content_metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Record content approval/rejection decision

        Args:
            tenant_id: Tenant identifier
            content_id: Content identifier
            decision: approved, rejected, or modified
            decision_reason: Reason for decision
            content_metadata: Content attributes (topic, type, keywords, etc.)

        Returns:
            Confirmation with pattern analysis
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        decision_record = {
            "content_id": content_id,
            "decision": decision,
            "reason": decision_reason,
            "metadata": content_metadata or {},
            "timestamp": timestamp,
        }

        self._approval_history[tenant_id].append(decision_record)

        # Learn from rejection patterns
        if decision == "rejected":
            topic = content_metadata.get("topic", "unknown") if content_metadata else "unknown"
            self._rejection_patterns[f"{tenant_id}:{topic}"] += 1

        # Update quality scores
        if decision == "approved":
            self._quality_scores[content_id] = 0.9
        elif decision == "modified":
            self._quality_scores[content_id] = 0.6
        elif decision == "rejected":
            self._quality_scores[content_id] = 0.2

        # Analyze patterns
        pattern_analysis = self._analyze_decision_patterns(tenant_id)

        logger.info(
            "Content decision recorded: %s → %s (%s)",
            content_id,
            decision,
            decision_reason or "no reason",
        )

        return {
            "recorded": True,
            "content_id": content_id,
            "decision": decision,
            "pattern_analysis": pattern_analysis,
            "total_decisions": len(self._approval_history[tenant_id]),
        }

    async def predict_content_quality(
        self,
        tenant_id: str,
        topic: str,
        content_type: str,
        keywords: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Predict content quality score before generation

        Args:
            tenant_id: Tenant identifier
            topic: Content topic
            content_type: Article, social, video, etc.
            keywords: Optional keywords

        Returns:
            Quality prediction with confidence and blocking recommendation
        """
        # Check historical performance for this topic
        topic_key = f"{tenant_id}:{topic}"
        rejection_count = self._rejection_patterns.get(topic_key, 0)

        # Get topic performance history
        topic_history = self._get_topic_history(tenant_id, topic)

        # Calculate predicted quality score
        if topic_history:
            avg_score = sum(h.get("quality_score", 0.5) for h in topic_history) / len(topic_history)
        else:
            avg_score = 0.5  # No history, neutral score

        # Adjust for rejection patterns
        if rejection_count > 3:
            avg_score *= 0.5  # Heavy penalty for repeated rejections
        elif rejection_count > 1:
            avg_score *= 0.75  # Moderate penalty

        # Determine if content should be blocked
        should_block = avg_score < 0.3
        confidence = min(0.95, 0.5 + (len(topic_history) * 0.1))

        recommendation = "block" if should_block else ("modify" if avg_score < 0.5 else "proceed")

        return {
            "predicted_quality_score": round(avg_score, 2),
            "confidence": round(confidence, 2),
            "recommendation": recommendation,
            "should_block": should_block,
            "rejection_history": rejection_count,
            "topic_history_count": len(topic_history),
            "blocking_reason": f"Topic '{topic}' has {rejection_count} prior rejections" if should_block else None,
        }

    async def get_feedback_for_content_engine(
        self,
        tenant_id: str,
        topic: str,
        content_type: str,
    ) -> Dict[str, Any]:
        """
        Get feedback for ContentEngine to improve future content

        Args:
            tenant_id: Tenant identifier
            topic: Content topic
            content_type: Content type

        Returns:
            Feedback with improvement suggestions
        """
        topic_history = self._get_topic_history(tenant_id, topic)

        # Analyze what worked vs what didn't
        approved_content = [h for h in topic_history if h.get("decision") == "approved"]
        rejected_content = [h for h in topic_history if h.get("decision") == "rejected"]

        feedback = {
            "topic": topic,
            "content_type": content_type,
            "total_history": len(topic_history),
            "approval_rate": len(approved_content) / max(1, len(topic_history)),
            "suggestions": [],
            "avoid_patterns": [],
        }

        # Extract patterns from approved content
        if approved_content:
            common_keywords = self._extract_common_keywords(approved_content)
            if common_keywords:
                feedback["suggestions"].append(f"Include keywords: {', '.join(common_keywords[:5])}")

            common_types = defaultdict(int)
            for item in approved_content:
                common_types[item.get("content_type", "unknown")] += 1
            if common_types:
                best_type = max(common_types, key=common_types.get)
                feedback["suggestions"].append(f"Preferred content type: {best_type}")

        # Extract patterns from rejected content
        if rejected_content:
            common_rejection_reasons = defaultdict(int)
            for item in rejected_content:
                reason = item.get("reason", "unknown")
                common_rejection_reasons[reason] += 1

            for reason, count in common_rejection_reasons.items():
                if count >= 2:
                    feedback["avoid_patterns"].append(f"Avoid: {reason} (rejected {count} times)")

        return feedback

    async def generate_quality_report(
        self,
        tenant_id: str,
        time_window: str = "7d",
    ) -> Dict[str, Any]:
        """
        Generate content quality report for tenant

        Args:
            tenant_id: Tenant identifier
            time_window: Time window (7d, 30d, 90d)

        Returns:
            Quality report with trends and recommendations
        """
        history = self._approval_history.get(tenant_id, [])

        # Filter by time window (simplified - would parse time_window properly)
        recent_history = history[-100:]  # Last 100 decisions

        if not recent_history:
            return {
                "tenant_id": tenant_id,
                "total_decisions": 0,
                "message": "No decision history available",
            }

        # Calculate metrics
        approved = sum(1 for h in recent_history if h["decision"] == "approved")
        rejected = sum(1 for h in recent_history if h["decision"] == "rejected")
        modified = sum(1 for h in recent_history if h["decision"] == "modified")

        approval_rate = approved / len(recent_history)

        # Find best and worst performing topics
        topic_performance = defaultdict(lambda: {"approved": 0, "rejected": 0, "total": 0})
        for h in recent_history:
            topic = h.get("metadata", {}).get("topic", "unknown")
            topic_performance[topic]["total"] += 1
            if h["decision"] == "approved":
                topic_performance[topic]["approved"] += 1
            elif h["decision"] == "rejected":
                topic_performance[topic]["rejected"] += 1

        # Sort by approval rate
        topic_rates = []
        for topic, stats in topic_performance.items():
            rate = stats["approved"] / max(1, stats["total"])
            topic_rates.append((topic, rate, stats))

        topic_rates.sort(key=lambda x: x[1], reverse=True)

        return {
            "tenant_id": tenant_id,
            "time_window": time_window,
            "total_decisions": len(recent_history),
            "approved": approved,
            "rejected": rejected,
            "modified": modified,
            "approval_rate": round(approval_rate, 2),
            "best_topics": [(t, round(r, 2)) for t, r, _ in topic_rates[:5]],
            "worst_topics": [(t, round(r, 2)) for t, r, _ in topic_rates[-5:]],
            "recommendations": self._generate_recommendations(topic_rates),
        }

    def _analyze_decision_patterns(self, tenant_id: str) -> Dict[str, Any]:
        """Analyze decision patterns for tenant"""
        history = self._approval_history.get(tenant_id, [])
        if not history:
            return {"pattern": "insufficient_data"}

        recent = history[-20:]
        approved = sum(1 for h in recent if h["decision"] == "approved")
        rejected = sum(1 for h in recent if h["decision"] == "rejected")

        if approved > rejected * 2:
            pattern = "high_approval"
        elif rejected > approved:
            pattern = "high_rejection"
        else:
            pattern = "mixed"

        return {
            "pattern": pattern,
            "recent_approval_rate": round(approved / len(recent), 2),
            "trend": "improving" if approved > len(recent) / 2 else "declining",
        }

    def _get_topic_history(self, tenant_id: str, topic: str) -> List[Dict[str, Any]]:
        """Get decision history for specific topic"""
        history = self._approval_history.get(tenant_id, [])
        return [
            h for h in history
            if h.get("metadata", {}).get("topic") == topic
        ]

    def _extract_common_keywords(self, content_list: List[Dict[str, Any]]) -> List[str]:
        """Extract common keywords from approved content"""
        keyword_counts = defaultdict(int)
        for item in content_list:
            keywords = item.get("metadata", {}).get("keywords", [])
            for kw in keywords:
                keyword_counts[kw] += 1

        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_keywords[:10]]

    def _generate_recommendations(self, topic_rates: List[tuple]) -> List[str]:
        """Generate recommendations based on topic performance"""
        recommendations = []

        if not topic_rates:
            return recommendations

        # Best topic recommendation
        if topic_rates[0][1] > 0.8:
            recommendations.append(f"Focus on '{topic_rates[0][0]}' - {round(topic_rates[0][1] * 100)}% approval rate")

        # Worst topic warning
        if topic_rates[-1][1] < 0.3:
            recommendations.append(f"Avoid or revise '{topic_rates[-1][0]}' - only {round(topic_rates[-1][1] * 100)}% approval rate")

        # Overall quality assessment
        avg_rate = sum(r for _, r, _ in topic_rates) / len(topic_rates)
        if avg_rate > 0.7:
            recommendations.append("Overall content quality is strong - maintain current standards")
        elif avg_rate < 0.4:
            recommendations.append("Content quality needs improvement - review approval criteria")

        return recommendations
