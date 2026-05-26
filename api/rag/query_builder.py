"""Semantic query construction for benchmark matching.

Builds optimized semantic search queries for finding benchmark clauses
that match specific risk categories, severity levels, and clause types.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import SearchQuery


class QueryBuilder:
    """Semantic query builder for benchmark matching.

    Constructs optimized search queries for retrieving benchmark
    clauses based on risk categories, severity levels, and clause
    characteristics. Supports multi-faceted query construction.

    Usage:
        builder = QueryBuilder()
        query = builder.build_category_query("indemnification", "high_risk")
        query = builder.build_benchmark_comparison_query(
            clause_text="...", category="liability_limitation"
        )
    """

    # Query templates for different search scenarios
    CATEGORY_PREFIXES: Dict[str, str] = {
        "indemnification": "indemnification clause regarding",
        "liability_limitation": "limitation of liability provision about",
        "termination": "termination clause concerning",
        "confidentiality": "confidentiality provision regarding",
        "data_privacy": "data privacy and security clause about",
        "compliance": "regulatory compliance provision regarding",
        "payment_terms": "payment terms and pricing clause about",
        "force_majeure": "force majeure provision concerning",
        "assignment": "assignment clause regarding",
        "governing_law": "governing law and jurisdiction provision",
        "non_compete": "non-compete and non-solicit clause about",
        "intellectual_property": "intellectual property provision regarding",
    }

    SEVERITY_MODIFIERS: Dict[str, str] = {
        "critical": "extremely aggressive one-sided unfavorable",
        "high": "highly unfavorable risky",
        "medium": "moderate standard typical",
        "low": "favorable balanced market standard",
        "info": "standard boilerplate",
    }

    def __init__(self) -> None:
        """Initialize the query builder."""
        pass

    def build_category_query(
        self,
        category: str,
        severity_tier: Optional[str] = None,
        sub_type: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchQuery:
        """Build a query for finding clauses in a specific category.

        Args:
            category: Risk category identifier.
            severity_tier: Optional severity filter.
            sub_type: Optional sub-type filter.
            top_k: Number of results.

        Returns:
            Configured SearchQuery.
        """
        prefix = self.CATEGORY_PREFIXES.get(category, f"{category} clause")
        severity_mod = self.SEVERITY_MODIFIERS.get(
            severity_tier or "", ""
        )

        query_parts = [prefix]
        if severity_mod:
            query_parts.append(severity_mod)
        if sub_type:
            query_parts.append(sub_type.replace("_", " "))

        query_text = " ".join(query_parts)

        metadata_filter: Dict[str, Any] = {"risk_category": category}
        if sub_type:
            metadata_filter["sub_type"] = sub_type

        return SearchQuery(
            query_text=query_text,
            top_k=top_k,
            category_filter=category,
            metadata_filter=metadata_filter,
        )

    def build_benchmark_comparison_query(
        self,
        clause_text: str,
        category: str,
        sub_type: Optional[str] = None,
    ) -> SearchQuery:
        """Build a query to find similar benchmark clauses.

        Extracts key terms from the clause and constructs a query
        optimized for finding comparable market-standard clauses.

        Args:
            clause_text: The clause text to compare.
            category: Risk category.
            sub_type: Optional sub-type.

        Returns:
            SearchQuery for benchmark comparison.
        """
        # Extract key phrases from the clause (first 200 chars)
        key_phrases = self._extract_key_phrases(clause_text)

        prefix = self.CATEGORY_PREFIXES.get(category, f"{category} clause")
        query_text = (
            f"{prefix} similar to: {key_phrases} "
            f"market standard version"
        )

        metadata_filter: Dict[str, Any] = {
            "risk_category": category,
            "is_benchmark": True,
        }
        if sub_type:
            metadata_filter["sub_type"] = sub_type

        return SearchQuery(
            query_text=query_text,
            top_k=5,
            category_filter=category,
            metadata_filter=metadata_filter,
            diversity_factor=0.4,
        )

    def build_similar_clause_query(
        self,
        clause_text: str,
        top_k: int = 5,
    ) -> SearchQuery:
        """Build a query to find semantically similar clauses.

        Uses the clause text directly as the query to find similar
        clauses across the corpus.

        Args:
            clause_text: The clause text to find similar matches for.
            top_k: Number of results.

        Returns:
            SearchQuery for similarity search.
        """
        # Use a concise version of the clause as the query
        query_text = self._extract_key_phrases(clause_text, max_chars=500)

        return SearchQuery(
            query_text=query_text,
            top_k=top_k,
            diversity_factor=0.3,
        )

    def build_multi_faceted_query(
        self,
        categories: List[str],
        severity_range: Optional[tuple[int, int]] = None,
        clause_type: Optional[str] = None,
        top_k: int = 10,
    ) -> SearchQuery:
        """Build a complex multi-faceted search query.

        Args:
            categories: List of risk categories to search.
            severity_range: Optional (min, max) severity filter.
            clause_type: Optional clause type filter.
            top_k: Number of results.

        Returns:
            SearchQuery with combined filters.
        """
        category_text = " or ".join(
            self.CATEGORY_PREFIXES.get(c, c) for c in categories
        )
        query_text = f"contract {category_text}"

        if clause_type:
            query_text += f" {clause_type}"

        metadata_filter: Dict[str, Any] = {}
        if len(categories) == 1:
            metadata_filter["risk_category"] = categories[0]
        if clause_type:
            metadata_filter["clause_type"] = clause_type

        return SearchQuery(
            query_text=query_text,
            top_k=top_k,
            metadata_filter=metadata_filter,
            diversity_factor=0.5,
        )

    def build_high_risk_query(
        self,
        category: str,
        top_k: int = 10,
    ) -> SearchQuery:
        """Build a query specifically for finding high-risk clauses.

        Args:
            category: Risk category.
            top_k: Number of results.

        Returns:
            SearchQuery optimized for high-risk clause retrieval.
        """
        prefix = self.CATEGORY_PREFIXES.get(category, category)
        query_text = (
            f"{prefix} with unfavorable aggressive one-sided terms "
            f"high risk to the other party"
        )

        return SearchQuery(
            query_text=query_text,
            top_k=top_k,
            category_filter=category,
            metadata_filter={"risk_category": category},
            diversity_factor=0.2,  # Lower diversity for high-risk focus
        )

    def build_market_standard_query(
        self,
        category: str,
        top_k: int = 5,
    ) -> SearchQuery:
        """Build a query for finding market-standard clauses.

        Args:
            category: Risk category.
            top_k: Number of results.

        Returns:
            SearchQuery optimized for market standard retrieval.
        """
        prefix = self.CATEGORY_PREFIXES.get(category, category)
        query_text = (
            f"{prefix} market standard balanced fair reasonable "
            f"typical commercial terms"
        )

        return SearchQuery(
            query_text=query_text,
            top_k=top_k,
            category_filter=category,
            metadata_filter={
                "risk_category": category,
                "is_benchmark": True,
            },
            diversity_factor=0.4,
        )

    def _extract_key_phrases(
        self, text: str, max_chars: int = 300
    ) -> str:
        """Extract key phrases from clause text.

        Takes the first meaningful portion of text, focusing on
        the most distinctive language.

        Args:
            text: The clause text.
            max_chars: Maximum characters to extract.

        Returns:
            Extracted key phrases.
        """
        # Remove common boilerplate
        cleaned = text.strip()
        if len(cleaned) <= max_chars:
            return cleaned

        # Try to find a good break point
        break_points = [". ", ";\n", ".\n"]
        truncated = cleaned[:max_chars]

        for bp in break_points:
            last_break = truncated.rfind(bp)
            if last_break > max_chars // 2:
                return truncated[:last_break + len(bp)]

        return truncated + "..."
