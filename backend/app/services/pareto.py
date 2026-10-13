"""
Pareto Analysis Service (80/20 Rule)
Calculates defect and root-cause frequency distributions with cumulative percentages.
Supports dimensions: defect_type, machine, product_family, root_cause, rejection_reason.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.db.models import QualityIncident, RCAHypothesis, Batch, Product, Machine
from backend.app.core.guardrails import EpistemicLabel

class ParetoService:
    """Computes Pareto distributions and isolates the vital few across 5 dimensions."""

    @staticmethod
    def _parse_date_bounds(start_date: Optional[str], end_date: Optional[str]):
        """
        Parses and validates inclusive start and end date bounds.
        Raises ValueError for invalid formats (mapped to 422) or reversed ranges (mapped to 400).
        """
        dt_start = None
        dt_end = None

        if start_date:
            try:
                s_str = start_date.strip()
                if len(s_str) == 10:
                    dt_start = datetime.strptime(s_str, "%Y-%m-%d")
                else:
                    dt_start = datetime.fromisoformat(s_str.replace("Z", "+00:00"))
                if dt_start.tzinfo is not None:
                    dt_start = dt_start.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                raise ValueError(f"Invalid start_date format: '{start_date}'. Expected ISO-8601 (YYYY-MM-DD).")

        if end_date:
            try:
                e_str = end_date.strip()
                if len(e_str) == 10:
                    dt_end = datetime.strptime(e_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
                else:
                    dt_end = datetime.fromisoformat(e_str.replace("Z", "+00:00"))
                if dt_end.tzinfo is not None:
                    dt_end = dt_end.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                raise ValueError(f"Invalid end_date format: '{end_date}'. Expected ISO-8601 (YYYY-MM-DD).")

        if dt_start and dt_end and dt_start > dt_end:
            raise ValueError(f"Reversed date range: start_date ({start_date}) cannot be later than end_date ({end_date}).")

        return dt_start, dt_end

    @staticmethod
    def compute_pareto(
        db: Session,
        dimension: str = "defect_type",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregates quality events by dimension and calculates cumulative percentages.
        Dimensions supported: defect_type, machine, product_family, root_cause, rejection_reason.
        """
        dt_start, dt_end = ParetoService._parse_date_bounds(start_date, end_date)

        query = db.query(QualityIncident)
        if dt_start:
            query = query.filter(QualityIncident.created_at >= dt_start)
        if dt_end:
            query = query.filter(QualityIncident.created_at <= dt_end)

        incidents = query.all()
        counts: Dict[str, int] = {}

        if dimension == "defect_type":
            for inc in incidents:
                key = inc.defect_type or "Unspecified"
                counts[key] = counts.get(key, 0) + 1

        elif dimension == "machine":
            for inc in incidents:
                key = inc.batch.machine.code if (inc.batch and inc.batch.machine and inc.batch.machine.code) else "Unspecified"
                counts[key] = counts.get(key, 0) + 1

        elif dimension == "product_family":
            for inc in incidents:
                key = inc.batch.product.family if (inc.batch and inc.batch.product and inc.batch.product.family) else "Unspecified"
                counts[key] = counts.get(key, 0) + 1

        elif dimension == "rejection_reason":
            for inc in incidents:
                key = inc.rejection_reason or "Unspecified"
                counts[key] = counts.get(key, 0) + 1

        elif dimension == "root_cause":
            # ONLY include confirmed root causes verified by Quality Engineers
            q = (
                db.query(RCAHypothesis)
                .join(QualityIncident, RCAHypothesis.incident_id == QualityIncident.id)
                .filter(
                    (RCAHypothesis.label == EpistemicLabel.CONFIRMED_ROOT_CAUSE.value) |
                    (RCAHypothesis.status == "confirmed")
                )
            )
            if dt_start:
                q = q.filter(QualityIncident.created_at >= dt_start)
            if dt_end:
                q = q.filter(QualityIncident.created_at <= dt_end)

            confirmed_hypos = q.all()
            for h in confirmed_hypos:
                key = h.title or "Unspecified"
                counts[key] = counts.get(key, 0) + 1

        else:
            # Fallback to defect_type
            for inc in incidents:
                key = inc.defect_type or "Unspecified"
                counts[key] = counts.get(key, 0) + 1

        total_occurrences = sum(counts.values())

        if not counts or total_occurrences == 0:
            return {
                "dimension": dimension,
                "total_incidents": 0,
                "total": 0,
                "categories_count": 0,
                "start_date": start_date,
                "end_date": end_date,
                "date_range_applied": f"{start_date or 'Earliest'} to {end_date or 'Latest'}",
                "vital_few_categories": [],
                "items": [],
                "label": EpistemicLabel.STATISTICAL_FINDING.value,
                "analysis_note": "No incidents found matching the specified criteria."
            }

        # Stable, deterministic tie-breaking: count descending, then category name ascending
        sorted_items = sorted(counts.items(), key=lambda x: (-x[1], str(x[0])))

        items_list = []
        cumulative_sum = 0
        vital_few = []
        vital_cutoff_reached = False

        for idx, (category, count) in enumerate(sorted_items):
            cumulative_sum += count
            pct = round((count / total_occurrences) * 100.0, 1)

            # Ensure cumulative percentage ends at exactly 100.0% for the final item
            if idx == len(sorted_items) - 1:
                cum_pct = 100.0
            else:
                cum_pct = round((cumulative_sum / total_occurrences) * 100.0, 1)

            # Vital few rule: categories included until cumulative percentage reaches 80.0%
            if not vital_cutoff_reached:
                vital_few.append(category)
                is_vital = True
                if cum_pct >= 80.0:
                    vital_cutoff_reached = True
            else:
                is_vital = False

            items_list.append({
                "category": category,
                "count": count,
                "percent": pct,
                "percentage": pct,
                "cumulative_percent": cum_pct,
                "cumulative_percentage": cum_pct,
                "is_vital_few": is_vital
            })

        note_prefix = "Confirmed causes only (Verified by Lead Quality Engineer). " if dimension == "root_cause" else ""
        return {
            "dimension": dimension,
            "total_incidents": total_occurrences,
            "total": total_occurrences,
            "start_date": start_date,
            "end_date": end_date,
            "date_range_applied": f"{start_date or 'Earliest'} to {end_date or 'Latest'}",
            "categories_count": len(items_list),
            "vital_few_categories": vital_few,
            "items": items_list,
            "label": EpistemicLabel.STATISTICAL_FINDING.value,
            "analysis_note": (
                f"{note_prefix}Categories contributing to 80% of recorded events isolated under Pareto 80/20 principle. "
                "Notice: Pareto frequency reflects observed event distribution and does not autonomously establish causation."
            )
        }

pareto_service = ParetoService()
