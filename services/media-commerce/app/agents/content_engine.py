"""
ContentEngine™ Agent

Autonomous content creation, SEO optimization, and distribution.
Implements the Media-to-Commerce workflow loop:
Keyword Clustering → Draft → Publish → Monitor → Optimize → Repurpose
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ContentEngineAgent:
    """
    ContentEngine™ Agent
    
    Capabilities:
    - Content strategy and topic identification
    - Copywriting and content generation
    - AI-SEO and programmatic SEO
    - Social content and ad creative
    - Content performance monitoring
    - Auto-optimization based on EPC
    """
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url
        self.skills_path = "app/skills"
        self._vertical_profiles = {
            "studio": {
                "content_types": ["portfolio", "case study", "proposal", "social"],
                "distribution_channels": ["referral", "seo", "email", "portfolio"],
                "default_goals": ["awareness", "leads"],
                "angles": ["case-study proof", "process clarity", "before-and-after results"],
            },
            "ecom": {
                "content_types": ["article", "product page", "email", "social", "ad"],
                "distribution_channels": ["seo", "email", "paid social", "marketplace"],
                "default_goals": ["sales", "conversions"],
                "angles": ["purchase intent", "offer framing", "conversion lift"],
            },
            "saas": {
                "content_types": ["article", "landing page", "webinar", "email", "social"],
                "distribution_channels": ["seo", "product marketing", "lifecycle email", "linkedin"],
                "default_goals": ["leads", "activation"],
                "angles": ["problem-solution", "integration story", "roi proof"],
            },
            "staffing": {
                "content_types": ["article", "case study", "email", "landing page", "social"],
                "distribution_channels": ["search", "outreach", "email", "local seo"],
                "default_goals": ["leads", "placements"],
                "angles": ["speed to fill", "credentialing readiness", "coverage gaps"],
            },
            "media": {
                "content_types": ["article", "video", "social", "email", "affiliate placement"],
                "distribution_channels": ["seo", "social", "newsletter", "affiliate"],
                "default_goals": ["awareness", "revenue"],
                "angles": ["topical authority", "distribution leverage", "epc lift"],
            },
        }
        self._retire_epc_threshold = 2.5
        self._double_down_epc_threshold = 10.0
        self._refresh_epc_threshold = 5.0
        self._mature_days_threshold = 7

    async def create_content_strategy(
        self,
        tenant_id: str,
        vertical: str,
        topic: str,
        goals: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Create content strategy using content-strategy skill
        
        Args:
            tenant_id: Tenant identifier
            vertical: Business vertical (studio, ecom, saas, staffing, media)
            topic: Main topic or keyword cluster
            goals: Content goals (awareness, leads, sales, etc.)
            
        Returns:
            Strategy with topics, angles, and content types
        """
        profile = self._get_vertical_profile(vertical)
        goals = self._normalize_terms(goals) or list(profile["default_goals"])

        # Load product marketing context
        context = await self._load_marketing_context(tenant_id)
        keywords = await self._research_keywords(topic)
        angles = self._generate_content_angles(topic, context, profile)
        recommended_actions = self._build_recommended_actions(topic, goals, profile, context)
        strategy = {
            "tenant_id": tenant_id,
            "vertical": vertical,
            "topic": topic,
            "goals": goals,
            "primary_goal": goals[0],
            "content_types": profile["content_types"],
            "distribution_channels": profile["distribution_channels"],
            "angles": angles,
            "keywords": keywords,
            "recommended_actions": recommended_actions,
            "content_brief": self._build_content_brief(topic, vertical, goals, context, keywords),
            "context_snapshot": {
                "product_name": context.get("product_name", "Product"),
                "brand_voice": context.get("brand_voice", "professional"),
                "target_audience": list(context.get("target_audience", [])),
                "value_propositions": list(context.get("value_propositions", [])),
            },
        }
        
        logger.info(f"Created content strategy for {topic}")
        return strategy
    
    async def generate_content(
        self,
        tenant_id: str,
        vertical: str,
        content_type: str,
        topic: str,
        keywords: List[str],
        tone: str = "professional",
    ) -> Dict[str, Any]:
        """
        Generate content using copywriting skill
        
        Args:
            tenant_id: Tenant identifier
            vertical: Business vertical
            content_type: article, video, social, ad, etc.
            topic: Content topic
            keywords: Target keywords
            tone: Brand voice/tone
            
        Returns:
            Generated content with metadata
        """
        # Load product marketing context
        context = await self._load_marketing_context(tenant_id)
        
        # Run copywriting skill logic
        content = {
            "tenant_id": tenant_id,
            "vertical": vertical,
            "type": content_type,
            "title": await self._generate_title(topic, keywords),
            "body": await self._generate_body(topic, keywords, tone, context),
            "keywords": keywords,
            "topic": topic,
            "status": "draft",
            "metadata": {
                "tone": tone,
                "word_count": 0,  # Will be calculated
                "reading_time": 0,
            },
        }
        
        # Save to database
        asset_id = await self._save_content_asset(content)
        content["id"] = asset_id
        
        logger.info(f"Generated {content_type} content for {topic}")
        return content
    
    async def optimize_for_ai_search(
        self,
        tenant_id: str,
        content_id: str,
    ) -> Dict[str, Any]:
        """
        Optimize content for AI search engines using ai-seo skill
        
        Args:
            tenant_id: Tenant identifier
            content_id: Content asset ID
            
        Returns:
            Optimization recommendations and structured data
        """
        # Load content
        content = await self._load_content_asset(content_id)
        if not content:
            return {"success": False, "error": "Content not found"}

        title = content.get("title") or content.get("topic") or content_id
        body = content.get("body") or content.get("summary") or ""
        keywords = self._normalize_terms(content.get("keywords"))
        structured_data = await self._generate_schema_markup(content)
        body_word_count = self._count_words(body)
        section_count = self._count_sections(body)
        citation_potential = self._calculate_citation_potential(
            {
                "body": body,
                "keywords": keywords,
                "structured_data": structured_data,
                "section_count": section_count,
            }
        )

        optimization = {
            "content_id": content_id,
            "title": title,
            "topic": content.get("topic") or title,
            "body_word_count": body_word_count,
            "keywords": keywords,
            "recommendations": [],
            "structured_data": structured_data,
            "llm_citation_potential": citation_potential,
            "citation_signals": {
                "has_summary": self._has_summary(body),
                "has_headings": section_count > 0,
                "has_keywords": bool(keywords),
                "word_count": body_word_count,
            },
        }

        if body_word_count < 450:
            optimization["recommendations"].append({
                "type": "depth",
                "message": "Expand the article body so the answer can be cited with enough context.",
                "priority": "high",
            })
        elif body_word_count < 900:
            optimization["recommendations"].append({
                "type": "depth",
                "message": "Add more supporting detail and examples to improve citation readiness.",
                "priority": "medium",
            })

        if not keywords:
            optimization["recommendations"].append({
                "type": "keywords",
                "message": "Add primary and supporting keywords for AI search relevance.",
                "priority": "high",
            })
        elif len(keywords) < 3:
            optimization["recommendations"].append({
                "type": "keywords",
                "message": "Add two or more supporting keywords to widen retrieval coverage.",
                "priority": "medium",
            })

        if not self._has_summary(body):
            optimization["recommendations"].append({
                "type": "summary",
                "message": "Add a concise opening summary that answers the query up front.",
                "priority": "medium",
            })

        if section_count == 0 and body_word_count >= 300:
            optimization["recommendations"].append({
                "type": "structure",
                "message": "Break the content into sections so citations can anchor on clear headings.",
                "priority": "medium",
            })

        if content.get("type") in {"article", "landing page", "guide"} and not self._has_cta(body):
            optimization["recommendations"].append({
                "type": "cta",
                "message": "Add a direct call to action to convert AI discovery into next steps.",
                "priority": "low",
            })
        
        logger.info(f"Optimized content {content_id} for AI search")
        return optimization
    
    async def monitor_performance(
        self,
        tenant_id: str,
        content_id: str = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Monitor content performance (EPC, views, conversions)
        
        Args:
            tenant_id: Tenant identifier
            content_id: Optional specific content ID
            days: Number of days to analyze
            
        Returns:
            Performance metrics and optimization recommendations
        """
        # Query events and content_assets for performance data
        performance = {
            "tenant_id": tenant_id,
            "period_days": days,
            "content_count": 0,
            "total_views": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "avg_epc": 0,
            "top_performers": [],
            "underperformers": [],
        }
        
        # In production, would query database for actual metrics
        # For now, return structure
        
        logger.info(f"Monitored performance for {tenant_id}")
        return performance
    
    async def auto_optimize(
        self,
        tenant_id: str,
        content_id: str,
    ) -> Dict[str, Any]:
        """
        Auto-optimize content based on performance
        
        Implements Scenario: IF EPC < threshold THEN optimize/retire
        
        Args:
            tenant_id: Tenant identifier
            content_id: Content asset ID
            
        Returns:
            Optimization actions taken
        """
        content = await self._load_content_asset(content_id)
        if not content:
            return {"success": False, "error": "Content not found"}
        
        performance = content.get("performance", {})
        epc = float(performance.get("epc") or 0)
        days_published = int(performance.get("days_published") or 0)
        views = int(performance.get("views") or 0)
        clicks = int(performance.get("clicks") or 0)
        conversions = int(performance.get("conversions") or 0)
        content_type = content.get("type") or "article"
        
        actions = {
            "content_id": content_id,
            "content_type": content_type,
            "current_epc": round(epc, 2),
            "days_published": days_published,
            "performance": {
                "views": views,
                "clicks": clicks,
                "conversions": conversions,
            },
            "decision": "monitor",
            "actions_taken": [],
            "thresholds": {
                "retire_epc": self._retire_epc_threshold,
                "double_down_epc": self._double_down_epc_threshold,
                "refresh_epc": self._refresh_epc_threshold,
                "mature_days": self._mature_days_threshold,
            },
        }
        
        # Policy: Retire content with EPC < $2.50 for 7+ days
        if epc < self._retire_epc_threshold and days_published >= self._mature_days_threshold:
            await self._retire_content(content_id)
            reason = (
                f"EPC ${epc:.2f} is below ${self._retire_epc_threshold:.2f} "
                f"after {days_published} published days"
            )
            actions["actions_taken"].append({
                "action": "retire",
                "reason": reason,
            })
            actions["decision"] = "retire"
            actions["status_after"] = "retired"
            actions["reason"] = reason
        
        # Policy: Double down on winners (EPC > $10)
        elif epc >= self._double_down_epc_threshold:
            # Create variations via ad-creative skill
            variations = await self._create_variations(content_id)
            reason = (
                f"EPC ${epc:.2f} meets or exceeds ${self._double_down_epc_threshold:.2f}; "
                f"create more variants while the asset is winning"
            )
            actions["actions_taken"].append({
                "action": "create_variations",
                "count": len(variations),
                "variations": variations,
                "reason": reason,
            })
            actions["decision"] = "scale"
            actions["status_after"] = "scaling"
            actions["reason"] = reason
        elif epc < self._refresh_epc_threshold and days_published >= 3:
            optimization = await self.optimize_for_ai_search(tenant_id, content_id)
            reason = (
                f"EPC ${epc:.2f} is below the refresh threshold; tighten AI-search readiness "
                "before scaling distribution"
            )
            actions["actions_taken"].append({
                "action": "refresh_ai_search",
                "recommendations": optimization.get("recommendations", []),
                "llm_citation_potential": optimization.get("llm_citation_potential", 0),
                "reason": reason,
            })
            actions["decision"] = "refresh"
            actions["status_after"] = "draft"
            actions["reason"] = reason
        else:
            actions["actions_taken"].append({
                "action": "monitor",
                "reason": "EPC and maturity are within the hold band; continue monitoring",
            })
            actions["reason"] = "EPC and maturity are within the hold band"
        
        logger.info(f"Auto-optimized content {content_id}: {actions}")
        return actions
    
    async def repurpose_content(
        self,
        tenant_id: str,
        content_id: str,
        target_formats: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Repurpose top-performing content across formats
        
        Args:
            tenant_id: Tenant identifier
            content_id: Source content ID
            target_formats: [social, video, email, ad]
            
        Returns:
            Repurposed content assets
        """
        target_formats = target_formats or ["social", "email"]
        
        content = await self._load_content_asset(content_id)
        if not content:
            return {"success": False, "error": "Content not found"}
        
        repurposed = {
            "source_id": content_id,
            "formats": [],
        }
        
        for fmt in target_formats:
            new_content = await self._transform_content(content, fmt)
            repurposed["formats"].append({
                "format": fmt,
                "content_id": new_content["id"],
                "status": new_content["status"],
            })
        
        logger.info(f"Repurposed content {content_id} into {len(target_formats)} formats")
        return repurposed
    
    # Internal helper methods
    
    async def _load_marketing_context(self, tenant_id: str) -> Dict[str, Any]:
        """Load product marketing context for tenant"""
        # In production, would load from .agents/product-marketing-context.md
        return {
            "tenant_id": tenant_id,
            "product_name": "Product",
            "target_audience": [],
            "value_propositions": [],
            "brand_voice": "professional",
        }

    def _generate_content_angles(self, topic: str, context: Dict, profile: Dict[str, Any] = None) -> List[str]:
        """Generate content angles from topic"""
        product_name = context.get("product_name", "Product")
        value_props = context.get("value_propositions", [])
        profile_angles = list((profile or {}).get("angles", []))
        angles = [
            f"How {product_name} solves {topic}",
            f"{topic} Best Practices",
            f"The Ultimate Guide to {topic}",
            f"{topic} Mistakes to Avoid",
        ]
        if value_props:
            angles.insert(1, f"{topic} through the lens of {value_props[0]}")
        if profile_angles:
            angles.append(f"{topic} with a {profile_angles[0]} angle")
        return self._dedupe_preserve_order(angles)

    async def _research_keywords(self, topic: str) -> List[str]:
        """Research keywords for topic"""
        # In production, would use ai-seo or programmatic-seo skill
        normalized_topic = self._normalize_text(topic)
        tokens = [token for token in re.findall(r"[a-z0-9]+", normalized_topic) if token not in self._stop_words()]
        keywords = [
            topic.strip(),
            f"best {topic.strip()}",
            f"how to {topic.strip()}",
        ]
        if len(tokens) >= 2:
            keywords.append(" ".join(tokens[:2]))
        if len(tokens) >= 3:
            keywords.append(" ".join(tokens[:3]))
        if tokens:
            keywords.append(tokens[0])
        return self._dedupe_preserve_order([kw for kw in keywords if kw])

    async def _generate_title(self, topic: str, keywords: List[str]) -> str:
        """Generate content title"""
        primary_keyword = keywords[0] if keywords else topic
        return f"The Complete Guide to {primary_keyword}"

    async def _generate_body(self, topic: str, keywords: List[str], tone: str, context: Dict) -> str:
        """Generate content body using copywriting skill"""
        # In production, would invoke copywriting skill via agent framework
        keyword_list = ", ".join(keywords[:3]) if keywords else topic
        product_name = context.get("product_name", "Product")
        return (
            f"{topic} is an important topic for {product_name}.\n\n"
            f"This {tone} overview focuses on {keyword_list}.\n\n"
            f"Use this draft to explain the problem, the approach, and the next step."
        )
    
    async def _save_content_asset(self, content: Dict[str, Any]) -> str:
        """Save content asset to database"""
        # In production, would insert into content_assets table
        import uuid
        return str(uuid.uuid4())
    
    async def _load_content_asset(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Load content asset from database"""
        # In production, would query content_assets table
        return {
            "id": content_id,
            "title": f"Content {content_id}",
            "topic": "default topic",
            "type": "article",
            "body": "Default article body with enough detail to be useful.\n\n# Section\nMore context.",
            "keywords": ["default topic", "content"],
            "performance": {"epc": 5.0, "days_published": 10, "views": 120, "clicks": 8, "conversions": 2},
            "metadata": {"author": "system"},
        }

    async def _generate_schema_markup(self, content: Dict) -> Dict[str, Any]:
        """Generate schema.org structured data"""
        keywords = self._normalize_terms(content.get("keywords"))
        body = content.get("body") or content.get("summary") or ""
        summary = self._first_sentence(body)
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": content.get("title") or content.get("topic"),
            "articleSection": content.get("type") or "article",
            "keywords": keywords,
            "about": content.get("topic") or content.get("title"),
            "wordCount": self._count_words(body),
            "citationEvidence": summary,
            "author": content.get("metadata", {}).get("author"),
        }

    def _calculate_citation_potential(self, content: Dict) -> float:
        """Calculate likelihood of AI/LLM citation"""
        body = content.get("body", "")
        keywords = content.get("keywords", [])
        structured_data = content.get("structured_data", {})
        section_count = int(content.get("section_count") or 0)

        score = 0.0
        score += min(self._count_words(body) / 2000.0, 0.35)
        score += min(len(keywords) / 5.0, 0.2)
        score += 0.2 if structured_data else 0.0
        score += 0.15 if self._has_summary(body) else 0.0
        score += 0.1 if section_count > 0 else 0.0
        return round(min(score, 1.0), 2)
    
    async def _retire_content(self, content_id: str):
        """Retire underperforming content"""
        # In production, would update content_assets.status = 'retired'
        logger.info(f"Retired content {content_id}")
    
    async def _create_variations(self, content_id: str) -> List[str]:
        """Create content variations via ad-creative skill"""
        # In production, would invoke ad-creative skill
        return [f"{content_id}-variation-1", f"{content_id}-variation-2"]
    
    async def _transform_content(self, content: Dict, target_format: str) -> Dict:
        """Transform content to different format"""
        # In production, would use social-content, video, or email-sequence skill
        import uuid
        return {
            "id": str(uuid.uuid4()),
            "type": target_format,
            "status": "draft",
        }

    def _get_vertical_profile(self, vertical: str) -> Dict[str, Any]:
        return self._vertical_profiles.get(vertical, {
            "content_types": ["article", "social", "email"],
            "distribution_channels": ["seo", "email", "social"],
            "default_goals": ["awareness", "leads"],
            "angles": ["clarity", "differentiation", "proof"],
        })

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    def _normalize_terms(self, values: Optional[List[str] | str]) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            raw_values = [values]
        else:
            raw_values = list(values)

        normalized: List[str] = []
        for value in raw_values:
            text = self._normalize_text(str(value))
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    def _dedupe_preserve_order(self, values: List[str]) -> List[str]:
        deduped: List[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped

    def _build_recommended_actions(
        self,
        topic: str,
        goals: List[str],
        profile: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        product_name = context.get("product_name", "Product")

        goal_actions = {
            "awareness": "publish a pillar article and distribute social snippets",
            "leads": "pair the content with a lead capture offer",
            "sales": "create a landing page and direct-response follow-up",
            "activation": "connect the content to onboarding and feature education",
            "retention": "add a nurture sequence and lifecycle follow-up",
            "revenue": "attach a conversion-focused CTA and attribution tracking",
            "placements": "anchor the piece in qualification and speed-to-fill messaging",
        }

        for goal in goals:
            action = goal_actions.get(goal)
            if action:
                actions.append({
                    "goal": goal,
                    "action": action,
                })

        actions.append({
            "goal": "distribution",
            "action": f"publish across {', '.join(profile['distribution_channels'])}",
        })
        actions.append({
            "goal": "positioning",
            "action": f"frame {topic} around {product_name} and the clearest proof point",
        })
        return actions

    def _build_content_brief(
        self,
        topic: str,
        vertical: str,
        goals: List[str],
        context: Dict[str, Any],
        keywords: List[str],
    ) -> Dict[str, Any]:
        return {
            "topic": topic,
            "vertical": vertical,
            "goals": goals,
            "audience": list(context.get("target_audience", [])),
            "primary_keyword": keywords[0] if keywords else topic,
            "supporting_keywords": keywords[1:4],
        }

    def _count_words(self, text: str) -> int:
        return len(re.findall(r"\b\w+\b", text or ""))

    def _count_sections(self, text: str) -> int:
        lines = [line.strip() for line in (text or "").splitlines()]
        return sum(1 for line in lines if line.startswith("#") or line.isupper())

    def _first_sentence(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
        return sentences[0] if sentences and sentences[0] else ""

    def _has_summary(self, text: str) -> bool:
        first_sentence = self._first_sentence(text)
        return bool(first_sentence and self._count_words(first_sentence) <= 28)

    def _has_cta(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(
            phrase in lowered
            for phrase in [
                "learn more",
                "book a demo",
                "get started",
                "contact us",
                "sign up",
                "request a demo",
            ]
        )

    def _stop_words(self) -> set[str]:
        return {
            "the", "and", "for", "with", "from", "into", "your", "you", "that",
            "this", "are", "our", "how", "best", "guide", "to", "of", "a", "an",
            "in", "on", "at", "by", "it", "is", "be", "or",
        }

    async def generate_programmatic_seo_pages(
        self,
        tenant_id: str,
        vertical: str,
        seed_keyword: str,
        template_id: str = None,
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Generate programmatic SEO pages at scale

        Args:
            tenant_id: Tenant identifier
            vertical: Business vertical
            seed_keyword: Seed keyword for cluster generation
            template_id: Optional template ID
            batch_size: Number of pages to generate

        Returns:
            Generated pages with keyword cluster
        """
        # Generate keyword cluster variations
        modifiers = ["best", "top", "guide", "how to", "vs", "alternatives", "for", "with"]
        keyword_cluster = [
            f"{modifier} {seed_keyword}"
            for modifier in modifiers[:batch_size]
        ]

        pages = []
        for keyword in keyword_cluster:
            pages.append({
                "keyword": keyword,
                "title": f"The Ultimate Guide to {keyword.title()}",
                "status": "draft",
            })

        logger.info(f"Generated {len(pages)} programmatic SEO pages for '{seed_keyword}'")

        return {
            "seed_keyword": seed_keyword,
            "vertical": vertical,
            "pages_generated": len(pages),
            "keyword_cluster": keyword_cluster,
            "pages": pages,
        }
