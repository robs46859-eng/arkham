"""
BudgetMind™ Agent

Autonomous financial planning and monitoring agent derived from best practices
used by top firms (McKinsey, BCG, Goldman Sachs, Sequoia, a16z).

Integrates with Digital Twin for scenario modeling and financial projections.

KEY CAPABILITIES:
- Budget monitoring with variance analysis
- Unit economics (CAC, LTV, payback, contribution margin)
- Cash flow projection (13-week rolling)
- Vendor consolidation and optimization
- Scenario planning (base, upside, downside)
- Financial policy enforcement
- Digital twin integration for modeling

DIGITAL TWIN INTEGRATION:
- Uses hardened digital twin from core for scenario modeling
- Twin provides: market conditions, competitor actions, operational constraints
- BudgetMind provides: financial models, projections, constraints
- Bidirectional sync for accurate what-if analysis
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import math

logger = logging.getLogger(__name__)


# =============================================================================
# FINANCIAL FRAMEWORKS (Top Firm Best Practices)
# =============================================================================

class SaaS_METRICS(Enum):
    """SaaS metrics benchmarks (Benchmark: SaaS Capital, OpenView, Bessemer)"""
    LTV_CAC_RATIO = 3.0  # Target: 3:1 or higher
    PAYBACK_MONTHS = 12  # Target: < 12 months
    GROSS_MARGIN = 0.75  # Target: 75%+
    NRR = 1.10  # Target: 110%+ (net revenue retention)
    CAC_RATIO = 0.33  # Target: CAC < 33% of first year revenue
    RULE_OF_40 = 40  # Target: Growth% + Profit% >= 40


class RETAIL_METRICS(Enum):
    """E-commerce/Retail benchmarks (Benchmark: McKinsey Retail, Bain)"""
    GROSS_MARGIN = 0.50  # Target: 50%+
    INVENTORY_TURNOVER = 6  # Target: 6x annually
    CONTRIBUTION_MARGIN = 0.25  # Target: 25%+
    CAC_PAYBACK = 3  # Target: < 3 months
    REPEAT_RATE = 0.35  # Target: 35%+ repeat customers


class STAFFING_METRICS(Enum):
    """Staffing agency benchmarks (Benchmark: Staffing Industry Analysts)"""
    GROSS_MARGIN = 0.25  # Target: 25%+
    FILL_RATE = 0.85  # Target: 85%+
    SUBMISSION_TO_INTERVIEW = 0.30  # Target: 30%+
    INTERVIEW_TO_OFFER = 0.25  # Target: 25%+
    OFFER_TO_ACCEPTANCE = 0.80  # Target: 80%+


class MEDIA_METRICS(Enum):
    """Media/Publisher benchmarks (Benchmark: Digiday, Axios Media)"""
    RPM = 25  # Revenue per mille (per 1000 impressions)
    CTR = 0.02  # Click-through rate: 2%
    EPC = 5.0  # Earnings per click: $5+
    CONVERSION_RATE = 0.03  # 3% conversion


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BudgetLine:
    """Budget line item with variance tracking"""
    category: str
    budgeted: float
    actual: float = 0.0
    committed: float = 0.0
    variance: float = field(init=False)
    variance_pct: float = field(init=False)
    status: str = field(init=False)

    def __post_init__(self):
        self.variance = self.budgeted - self.actual
        self.variance_pct = (self.variance / max(1, self.budgeted)) * 100
        if self.variance_pct >= 0:
            self.status = "on_track"
        elif self.variance_pct >= -10:
            self.status = "warning"
        else:
            self.status = "over_budget"


@dataclass
class UnitEconomics:
    """Unit economics calculation results"""
    cac: float  # Customer Acquisition Cost
    ltv: float  # Lifetime Value
    ltv_cac_ratio: float
    payback_months: float
    contribution_margin: float
    contribution_margin_pct: float
    arpu: float  # Average Revenue Per User
    churn_rate: float
    gross_margin: float


@dataclass
class CashFlowProjection:
    """13-week cash flow projection"""
    week_number: int
    starting_cash: float
    cash_in: float
    cash_out: float
    net_cash_flow: float
    ending_cash: float
    runway_days: float
    burn_rate: float


@dataclass
class ScenarioResult:
    """Scenario planning result from digital twin"""
    scenario_name: str
    revenue: float
    expenses: float
    ebitda: float
    cash_end: float
    key_assumptions: Dict[str, Any]
    risks: List[str]
    recommendations: List[str]


# =============================================================================
# BUDGETMIND AGENT
# =============================================================================

class BudgetMindAgent:
    """
    BudgetMind™ Agent - Financial Planning & Monitoring

    Derived from best practices used by:
    - McKinsey: Zero-based budgeting, variance analysis
    - BCG: Strategic cost management
    - Goldman Sachs: Cash flow modeling
    - Sequoia/a16z: SaaS metrics, unit economics
    - Y Combinator: 13-week cash flow

    DIGITAL TWIN INTEGRATION:
    - Scenario modeling uses hardened digital twin from core
    - Twin provides market/operational context
    - BudgetMind provides financial models and constraints
    """

    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url

        # Industry benchmarks
        self.benchmarks = {
            "saas": SaaS_METRICS,
            "retail": RETAIL_METRICS,
            "staffing": STAFFING_METRICS,
            "media": MEDIA_METRICS,
        }

        # Digital twin connection (hardened in core)
        self._digital_twin = None

        # Compounded memory from MediationAgent (read-only)
        self._compounded_memory: Dict[str, Any] = {}

    # =========================================================================
    # DIGITAL TWIN INTEGRATION
    # =========================================================================

    def connect_digital_twin(self, twin_interface: Any):
        """
        Connect to hardened digital twin from core

        The digital twin provides:
        - Market condition simulations
        - Competitor action modeling
        - Operational constraint validation
        - What-if scenario execution
        """
        self._digital_twin = twin_interface
        logger.info("BudgetMind connected to digital twin")

    async def run_scenario(
        self,
        scenario_name: str,
        assumptions: Dict[str, Any],
        time_horizon_months: int = 12,
    ) -> ScenarioResult:
        """
        Run financial scenario using digital twin

        Args:
            scenario_name: Name of scenario (base, upside, downside)
            assumptions: Financial and operational assumptions
            time_horizon_months: Projection horizon

        Returns:
            Scenario result with financial projections
        """
        if not self._digital_twin:
            logger.warning("Digital twin not connected, using basic projection")
            return self._basic_scenario(scenario_name, assumptions, time_horizon_months)

        # Use digital twin for sophisticated modeling
        twin_result = await self._digital_twin.simulate_scenario(
            scenario_name=scenario_name,
            financial_assumptions=assumptions,
            time_horizon=time_horizon_months,
        )

        return ScenarioResult(
            scenario_name=scenario_name,
            revenue=twin_result.get("revenue", 0),
            expenses=twin_result.get("expenses", 0),
            ebitda=twin_result.get("ebitda", 0),
            cash_end=twin_result.get("cash_end", 0),
            key_assumptions=twin_result.get("assumptions", {}),
            risks=twin_result.get("risks", []),
            recommendations=twin_result.get("recommendations", []),
        )

    def _basic_scenario(
        self,
        scenario_name: str,
        assumptions: Dict[str, Any],
        time_horizon_months: int,
    ) -> ScenarioResult:
        """Basic scenario calculation without digital twin"""
        base_revenue = assumptions.get("base_revenue", 100000)
        growth_rate = assumptions.get("growth_rate", 0.10)
        expense_ratio = assumptions.get("expense_ratio", 0.70)

        # Apply scenario multipliers
        multipliers = {
            "base": 1.0,
            "upside": 1.25,
            "downside": 0.70,
            "stress": 0.50,
        }
        multiplier = multipliers.get(scenario_name, 1.0)

        projected_revenue = base_revenue * multiplier
        projected_expenses = projected_revenue * expense_ratio
        ebitda = projected_revenue - projected_expenses

        return ScenarioResult(
            scenario_name=scenario_name,
            revenue=projected_revenue,
            expenses=projected_expenses,
            ebitda=ebitda,
            cash_end=assumptions.get("starting_cash", 500000) + (ebitda * time_horizon_months),
            key_assumptions=assumptions,
            risks=self._identify_scenario_risks(scenario_name, assumptions),
            recommendations=self._generate_scenario_recommendations(scenario_name, assumptions),
        )

    def _identify_scenario_risks(
        self,
        scenario_name: str,
        assumptions: Dict[str, Any],
    ) -> List[str]:
        """Identify risks for scenario"""
        risks = []

        if scenario_name == "downside":
            risks.append("Revenue shortfall may require expense reduction")
            risks.append("Cash runway may be impacted")
        elif scenario_name == "stress":
            risks.append("Critical cash position - immediate action required")
            risks.append("Consider emergency funding or rapid cost reduction")

        if assumptions.get("burn_rate", 0) > assumptions.get("revenue", 0) * 0.5:
            risks.append("High burn rate relative to revenue")

        return risks

    def _generate_scenario_recommendations(
        self,
        scenario_name: str,
        assumptions: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations for scenario"""
        recommendations = []

        if scenario_name in ("downside", "stress"):
            recommendations.append("Reduce non-essential expenses by 20-30%")
            recommendations.append("Delay non-critical hiring")
            recommendations.append("Extend cash runway through receivables acceleration")

        if assumptions.get("ltv_cac_ratio", 3) < 2:
            recommendations.append("Improve unit economics before scaling spend")

        if assumptions.get("runway_months", 12) < 6:
            recommendations.append("Initiate fundraising process immediately")

        return recommendations

    # =========================================================================
    # BUDGET MONITORING (McKinsey Zero-Based Budgeting)
    # =========================================================================

    async def monitor_budget(
        self,
        tenant_id: str,
        department: str = None,
        period: str = "month",
    ) -> Dict[str, Any]:
        """
        Monitor budget vs actual with variance analysis

        Args:
            tenant_id: Tenant identifier
            department: Optional department filter
            period: Reporting period (week, month, quarter)

        Returns:
            Budget monitoring with variance analysis
        """
        # Simulated budget lines (would query ledger in production)
        budget_lines = self._get_budget_lines(tenant_id, department)

        # Calculate totals
        total_budgeted = sum(bl.budgeted for bl in budget_lines)
        total_actual = sum(bl.actual for bl in budget_lines)
        total_variance = total_budgeted - total_actual
        variance_pct = (total_variance / max(1, total_budgeted)) * 100

        # Identify over-budget items
        over_budget = [bl for bl in budget_lines if bl.status == "over_budget"]
        warnings = [bl for bl in budget_lines if bl.status == "warning"]

        # Get compounded memory context for spending patterns
        memory_context = self._get_compounded_memory_insights()

        return {
            "tenant_id": tenant_id,
            "department": department or "all",
            "period": period,
            "total_budgeted": total_budgeted,
            "total_actual": total_actual,
            "total_variance": total_variance,
            "variance_pct": round(variance_pct, 2),
            "budget_lines": [
                {
                    "category": bl.category,
                    "budgeted": bl.budgeted,
                    "actual": bl.actual,
                    "variance": bl.variance,
                    "variance_pct": round(bl.variance_pct, 2),
                    "status": bl.status,
                }
                for bl in budget_lines
            ],
            "over_budget_count": len(over_budget),
            "warning_count": len(warnings),
            "over_budget_items": over_budget,
            "recommendations": self._generate_budget_recommendations(over_budget, warnings),
            "compounded_memory_context": memory_context,
        }

    def _get_budget_lines(self, tenant_id: str, department: str = None) -> List[BudgetLine]:
        """Get budget lines for tenant (simulated)"""
        # Default budget structure (would come from database)
        default_lines = [
            ("Sales & Marketing", 50000, 48000, 2000),
            ("Product & Engineering", 80000, 82000, -2000),
            ("G&A", 20000, 18000, 2000),
            ("Customer Success", 25000, 24000, 1000),
            ("R&D", 15000, 16000, -1000),
        ]

        return [
            BudgetLine(category=cat, budgeted=budget, actual=actual)
            for cat, budget, actual, _ in default_lines
        ]

    def _generate_budget_recommendations(
        self,
        over_budget: List[BudgetLine],
        warnings: List[BudgetLine],
    ) -> List[str]:
        """Generate budget recommendations"""
        recommendations = []

        for bl in over_budget:
            recommendations.append(
                f"Review {bl.category}: {abs(bl.variance_pct):.0f}% over budget (${abs(bl.variance):,.0f})"
            )

        if len(over_budget) >= 2:
            recommendations.append("Consider zero-based budget review for next period")

        if warnings:
            recommendations.append(f"Monitor {len(warnings)} categories approaching budget limits")

        return recommendations

    # =========================================================================
    # UNIT ECONOMICS (Sequoia/a16z Framework)
    # =========================================================================

    async def calculate_unit_economics(
        self,
        tenant_id: str,
        vertical: str,
        period_months: int = 3,
    ) -> Dict[str, Any]:
        """
        Calculate unit economics using top-firm formulas

        Formulas derived from:
        - Sequoia: SaaS metrics framework
        - a16z: Growth efficiency metrics
        - McKinsey: Unit economics deep dive

        Args:
            tenant_id: Tenant identifier
            vertical: Business vertical
            period_months: Analysis period

        Returns:
            Unit economics with benchmark comparison
        """
        # Simulated metrics (would query ledger in production)
        metrics = self._get_vertical_metrics(tenant_id, vertical, period_months)

        # Calculate unit economics
        unit_economics = self._calculate_unit_economics_from_metrics(metrics, vertical)

        # Get benchmarks for vertical
        benchmarks = self._get_benchmarks(vertical)

        # Compare to benchmarks
        benchmark_comparison = self._compare_to_benchmarks(unit_economics, benchmarks)

        return {
            "tenant_id": tenant_id,
            "vertical": vertical,
            "period_months": period_months,
            "unit_economics": {
                "cac": round(unit_economics.cac, 2),
                "ltv": round(unit_economics.ltv, 2),
                "ltv_cac_ratio": round(unit_economics.ltv_cac_ratio, 2),
                "payback_months": round(unit_economics.payback_months, 1),
                "contribution_margin": round(unit_economics.contribution_margin, 2),
                "contribution_margin_pct": round(unit_economics.contribution_margin_pct, 1),
                "arpu": round(unit_economics.arpu, 2),
                "churn_rate": round(unit_economics.churn_rate, 3),
                "gross_margin": round(unit_economics.gross_margin, 3),
            },
            "benchmarks": benchmark_comparison,
            "recommendations": self._generate_unit_economics_recommendations(
                unit_economics, benchmarks
            ),
        }

    def _get_vertical_metrics(
        self,
        tenant_id: str,
        vertical: str,
        period_months: int,
    ) -> Dict[str, float]:
        """Get metrics for vertical (simulated)"""
        return {
            "sales_marketing_spend": 150000,
            "new_customers": 50,
            "revenue": 500000,
            "cogs": 125000,
            "variable_costs": 75000,
            "customers_start": 200,
            "customers_end": 240,
            "customers_churned": 10,
            "arpu": 2083,
        }

    def _calculate_unit_economics_from_metrics(
        self,
        metrics: Dict[str, float],
        vertical: str,
    ) -> UnitEconomics:
        """Calculate unit economics from raw metrics"""
        # CAC = Sales & Marketing Spend / New Customers
        cac = metrics["sales_marketing_spend"] / max(1, metrics["new_customers"])

        # Gross Margin = (Revenue - COGS) / Revenue
        gross_margin = (metrics["revenue"] - metrics["cogs"]) / max(1, metrics["revenue"])

        # ARPU = Revenue / Average Customers
        avg_customers = (metrics["customers_start"] + metrics["customers_end"]) / 2
        arpu = metrics["revenue"] / max(1, avg_customers)

        # Churn Rate = Customers Churned / Customers Start
        churn_rate = metrics["customers_churned"] / max(1, metrics["customers_start"])

        # LTV = ARPU × Gross Margin × (1 / Churn Rate)
        # Simplified: assuming monthly recurring
        ltv = arpu * gross_margin * (1 / max(0.01, churn_rate))

        # LTV:CAC Ratio
        ltv_cac_ratio = ltv / max(1, cac)

        # Payback Period = CAC / (ARPU × Gross Margin)
        payback_months = cac / max(1, arpu * gross_margin)

        # Contribution Margin = Revenue - Variable Costs
        contribution_margin = metrics["revenue"] - metrics["variable_costs"]
        contribution_margin_pct = contribution_margin / max(1, metrics["revenue"])

        return UnitEconomics(
            cac=cac,
            ltv=ltv,
            ltv_cac_ratio=ltv_cac_ratio,
            payback_months=payback_months,
            contribution_margin=contribution_margin,
            contribution_margin_pct=contribution_margin_pct,
            arpu=arpu,
            churn_rate=churn_rate,
            gross_margin=gross_margin,
        )

    def _get_benchmarks(self, vertical: str) -> Dict[str, float]:
        """Get industry benchmarks for vertical"""
        benchmark_enum = self.benchmarks.get(vertical, SaaS_METRICS)

        return {
            "ltv_cac_ratio": benchmark_enum.LTV_CAC_RATIO.value,
            "payback_months": benchmark_enum.PAYBACK_MONTHS.value,
            "gross_margin": benchmark_enum.GROSS_MARGIN.value,
        }

    def _compare_to_benchmarks(
        self,
        unit_economics: UnitEconomics,
        benchmarks: Dict[str, float],
    ) -> Dict[str, Any]:
        """Compare unit economics to benchmarks"""
        return {
            "ltv_cac_ratio": {
                "actual": round(unit_economics.ltv_cac_ratio, 2),
                "benchmark": benchmarks["ltv_cac_ratio"],
                "status": "good" if unit_economics.ltv_cac_ratio >= benchmarks["ltv_cac_ratio"] else "needs_improvement",
            },
            "payback_months": {
                "actual": round(unit_economics.payback_months, 1),
                "benchmark": benchmarks["payback_months"],
                "status": "good" if unit_economics.payback_months <= benchmarks["payback_months"] else "needs_improvement",
            },
            "gross_margin": {
                "actual": round(unit_economics.gross_margin * 100, 1),
                "benchmark": benchmarks["gross_margin"] * 100,
                "status": "good" if unit_economics.gross_margin >= benchmarks["gross_margin"] else "needs_improvement",
            },
        }

    def _generate_unit_economics_recommendations(
        self,
        unit_economics: UnitEconomics,
        benchmarks: Dict[str, float],
    ) -> List[str]:
        """Generate recommendations based on unit economics"""
        recommendations = []

        if unit_economics.ltv_cac_ratio < benchmarks["ltv_cac_ratio"]:
            recommendations.append(
                f"LTV:CAC ratio ({unit_economics.ltv_cac_ratio:.1f}:1) below benchmark "
                f"({benchmarks['ltv_cac_ratio']}:1). Focus on retention or reduce CAC."
            )

        if unit_economics.payback_months > benchmarks["payback_months"]:
            recommendations.append(
                f"Payback period ({unit_economics.payback_months:.1f} months) exceeds "
                f"benchmark ({benchmarks['payback_months']} months). Consider pricing or CAC optimization."
            )

        if unit_economics.gross_margin < benchmarks["gross_margin"]:
            recommendations.append(
                f"Gross margin ({unit_economics.gross_margin*100:.1f}%) below "
                f"benchmark ({benchmarks['gross_margin']*100:.1f}%). Review COGS."
            )

        if unit_economics.churn_rate > 0.05:
            recommendations.append(
                f"Churn rate ({unit_economics.churn_rate*100:.1f}%) is high. "
                "Prioritize customer success initiatives."
            )

        return recommendations

    # =========================================================================
    # CASH FLOW PROJECTION (Y Combinator 13-Week Model)
    # =========================================================================

    async def project_cash_flow(
        self,
        tenant_id: str,
        weeks: int = 13,
        include_scenarios: bool = True,
    ) -> Dict[str, Any]:
        """
        Project 13-week cash flow (Y Combinator standard)

        Args:
            tenant_id: Tenant identifier
            weeks: Projection horizon (default 13 weeks)
            include_scenarios: Include scenario analysis

        Returns:
            Cash flow projection with runway analysis
        """
        # Starting position (would query ledger in production)
        starting_cash = 500000
        weekly_burn = 35000
        weekly_inflow = 25000

        projections = []
        current_cash = starting_cash

        for week in range(1, weeks + 1):
            # Simulate weekly cash flow
            cash_in = weekly_inflow * (1 + (week * 0.02))  # 2% weekly growth
            cash_out = weekly_burn * (1 + (week * 0.01))  # 1% weekly increase
            net_flow = cash_in - cash_out
            ending_cash = current_cash + net_flow

            # Calculate runway
            if net_flow < 0:
                runway_days = ending_cash / max(1, abs(net_flow)) * 7
            else:
                runway_days = float('inf')

            projections.append(CashFlowProjection(
                week_number=week,
                starting_cash=current_cash,
                cash_in=cash_in,
                cash_out=cash_out,
                net_cash_flow=net_flow,
                ending_cash=ending_cash,
                runway_days=runway_days,
                burn_rate=weekly_burn,
            ))

            current_cash = ending_cash

        # Identify cash alerts
        cash_alerts = [p for p in projections if p.ending_cash < 100000]
        negative_flow_weeks = [p for p in projections if p.net_cash_flow < 0]

        return {
            "tenant_id": tenant_id,
            "projection_weeks": weeks,
            "starting_cash": starting_cash,
            "ending_cash": projections[-1].ending_cash if projections else starting_cash,
            "weekly_projections": [
                {
                    "week": p.week_number,
                    "starting_cash": p.starting_cash,
                    "cash_in": p.cash_in,
                    "cash_out": p.cash_out,
                    "net_flow": p.net_cash_flow,
                    "ending_cash": p.ending_cash,
                    "runway_days": round(p.runway_days, 0) if p.runway_days != float('inf') else "N/A",
                }
                for p in projections
            ],
            "cash_alerts": len(cash_alerts),
            "negative_flow_weeks": len(negative_flow_weeks),
            "recommendations": self._generate_cash_flow_recommendations(projections),
        }

    def _generate_cash_flow_recommendations(
        self,
        projections: List[CashFlowProjection],
    ) -> List[str]:
        """Generate cash flow recommendations"""
        recommendations = []

        # Check for low cash
        final_cash = projections[-1].ending_cash if projections else 0
        if final_cash < 100000:
            recommendations.append(f"Projected cash (${final_cash:,.0f}) below safe minimum. Raise funding or reduce burn.")

        # Check for negative flow
        negative_weeks = [p for p in projections if p.net_cash_flow < 0]
        if len(negative_weeks) > len(projections) / 2:
            recommendations.append("Majority of weeks show negative cash flow. Review expense structure.")

        # Check runway
        final_runway = projections[-1].runway_days if projections else 0
        if final_runway != float('inf') and final_runway < 90:
            recommendations.append(f"Projected runway ({final_runway:.0f} days) below 90-day minimum.")

        return recommendations

    # =========================================================================
    # VENDOR CONSOLIDATION (McKinsey Strategic Cost Management)
    # =========================================================================

    async def consolidate_vendors(
        self,
        tenant_id: str,
        category: str = None,
    ) -> Dict[str, Any]:
        """
        Identify vendor consolidation opportunities

        Based on McKinsey strategic cost management framework:
        - Identify redundant tools/services
        - Calculate consolidation savings
        - Prioritize by effort vs. impact

        Args:
            tenant_id: Tenant identifier
            category: Optional category filter

        Returns:
            Vendor consolidation recommendations
        """
        # Simulated vendor data (would query ledger in production)
        vendors = self._get_vendor_data(tenant_id, category)

        # Identify redundancies
        redundancies = self._identify_vendor_redundancies(vendors)

        # Calculate savings
        savings_opportunities = self._calculate_consolidation_savings(redundancies)

        # Prioritize by effort vs. impact
        prioritized = self._prioritize_opportunities(savings_opportunities)

        return {
            "tenant_id": tenant_id,
            "category": category or "all",
            "total_vendors": len(vendors),
            "total_spend": sum(v["annual_spend"] for v in vendors),
            "redundancies_found": len(redundancies),
            "consolidation_opportunities": prioritized,
            "total_potential_savings": sum(o["annual_savings"] for o in prioritized),
            "recommendations": self._generate_vendor_recommendations(prioritized),
        }

    def _get_vendor_data(self, tenant_id: str, category: str = None) -> List[Dict]:
        """Get vendor data (simulated)"""
        return [
            {"name": "Slack", "category": "communication", "annual_spend": 12000, "users": 50},
            {"name": "Microsoft Teams", "category": "communication", "annual_spend": 8000, "users": 30},
            {"name": "Zoom", "category": "communication", "annual_spend": 5000, "users": 50},
            {"name": "Salesforce", "category": "crm", "annual_spend": 50000, "users": 20},
            {"name": "HubSpot", "category": "crm", "annual_spend": 25000, "users": 15},
            {"name": "AWS", "category": "infrastructure", "annual_spend": 100000, "users": None},
            {"name": "GCP", "category": "infrastructure", "annual_spend": 50000, "users": None},
        ]

    def _identify_vendor_redundancies(
        self,
        vendors: List[Dict],
    ) -> List[Dict]:
        """Identify redundant vendors by category"""
        by_category = {}
        for vendor in vendors:
            cat = vendor["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(vendor)

        redundancies = []
        for category, cat_vendors in by_category.items():
            if len(cat_vendors) > 1:
                redundancies.append({
                    "category": category,
                    "vendors": cat_vendors,
                    "total_spend": sum(v["annual_spend"] for v in cat_vendors),
                })

        return redundancies

    def _calculate_consolidation_savings(
        self,
        redundancies: List[Dict],
    ) -> List[Dict]:
        """Calculate potential savings from consolidation"""
        opportunities = []

        for redundancy in redundancies:
            vendors = redundancy["vendors"]
            total_spend = redundancy["total_spend"]

            # Identify primary (highest spend) and secondary vendors
            vendors_sorted = sorted(vendors, key=lambda v: v["annual_spend"], reverse=True)
            primary = vendors_sorted[0]
            secondary = vendors_sorted[1:]

            # Estimate savings (conservative: 50% of secondary vendor costs)
            secondary_spend = sum(v["annual_spend"] for v in secondary)
            estimated_savings = secondary_spend * 0.50

            opportunities.append({
                "category": redundancy["category"],
                "action": f"Consolidate to {primary['name']}",
                "current_vendors": [v["name"] for v in vendors],
                "recommended_vendor": primary["name"],
                "current_spend": total_spend,
                "projected_spend": total_spend - estimated_savings,
                "annual_savings": estimated_savings,
                "effort": "medium" if len(vendors) > 2 else "low",
                "impact": "high" if estimated_savings > 10000 else "medium",
            })

        return opportunities

    def _prioritize_opportunities(
        self,
        opportunities: List[Dict],
    ) -> List[Dict]:
        """Prioritize by effort vs. impact"""
        effort_scores = {"low": 1, "medium": 2, "high": 3}
        impact_scores = {"high": 3, "medium": 2, "low": 1}

        for opp in opportunities:
            opp["priority_score"] = (
                impact_scores.get(opp["impact"], 2) / effort_scores.get(opp["effort"], 2)
            )

        return sorted(opportunities, key=lambda x: x["priority_score"], reverse=True)

    def _generate_vendor_recommendations(
        self,
        opportunities: List[Dict],
    ) -> List[str]:
        """Generate vendor consolidation recommendations"""
        recommendations = []

        if not opportunities:
            recommendations.append("No significant vendor redundancies identified.")
            return recommendations

        top_opp = opportunities[0]
        recommendations.append(
            f"Priority: Consolidate {top_opp['category']} vendors to {top_opp['recommended_vendor']} "
            f"(save ${top_opp['annual_savings']:,.0f}/year)"
        )

        total_savings = sum(o["annual_savings"] for o in opportunities)
        recommendations.append(f"Total potential annual savings: ${total_savings:,.0f}")

        return recommendations

    # =========================================================================
    # COMPOUNDED MEMORY (READ-ONLY from MediationAgent)
    # =========================================================================

    def update_compounded_memory(self, memory: Dict[str, Any]):
        """Update compounded memory from MediationAgent (READ-ONLY)"""
        self._compounded_memory = memory.copy()
        logger.info("BudgetMind compounded memory updated")

    def _get_compounded_memory_insights(self) -> Dict[str, Any]:
        """Get insights from compounded memory for budget decisions"""
        if not self._compounded_memory:
            return {"status": "no_memory"}

        return {
            "approval_rate": self._compounded_memory.get("approval_rate", 0),
            "spending_patterns": self._compounded_memory.get("spending_patterns", {}),
            "rejected_categories": self._compounded_memory.get("rejection_patterns", {}),
        }
