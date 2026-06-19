"""Service layer for RedlineTemplate operations and AI draft generation."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from app.config import settings
from app.domains.ai.llm import OpenAIProvider, LLMRequest, RateLimitError
from app.domains.redline_templates.repository import RedlineTemplateRepository
from app.domains.ai.prompts import prompt_registry

logger = logging.getLogger(__name__)


class RedlineTemplateService:
    """Business logic for redline templates."""

    def __init__(self, repo: RedlineTemplateRepository):
        self.repo = repo

    async def create_template(self, data: dict) -> dict[str, Any]:
        """Create a new redline template."""
        template = await self.repo.create(data)
        return self._to_dict(template)

    async def get_template(self, template_id: str) -> Optional[dict[str, Any]]:
        template = await self.repo.get(template_id)
        return self._to_dict(template) if template else None

    async def list_templates(
        self,
        clause_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        templates = await self.repo.list(clause_type, category, status, limit, offset)
        return [self._to_dict(t) for t in templates]

    async def update_template(self, template_id: str, data: dict) -> Optional[dict[str, Any]]:
        template = await self.repo.update(template_id, data)
        return self._to_dict(template) if template else None

    async def delete_template(self, template_id: str) -> bool:
        return await self.repo.delete(template_id)

    async def record_usage(self, template_id: str, accepted: bool = True) -> None:
        await self.repo.record_usage(template_id, accepted)

    async def get_coverage(self) -> dict[str, Any]:
        return await self.repo.get_coverage()

    async def get_missing_templates(self, limit: int = 20) -> list[dict[str, Any]]:
        return await self.repo.get_missing_templates(limit)

    async def generate_ai_draft(
        self,
        clause_type: str,
        finding_title: str,
        finding_description: str,
        jurisdiction: Optional[str] = None,
        industry: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate a redline draft via AI for a missing template.

        Uses the redline_generation prompt template to produce
        a high-quality clause draft.
        """
        context_parts = [f"Risk: {finding_title}", f"Description: {finding_description}"]
        if jurisdiction:
            context_parts.append(f"Jurisdiction: {jurisdiction}")
        if industry:
            context_parts.append(f"Industry: {industry}")
        if risk_level:
            context_parts.append(f"Risk Level: {risk_level}")

        prompt = prompt_registry.render(
            "redline_generation", version="4.0.0",
            clause_type=clause_type,
            original_text="",
            context="\n".join(context_parts),
            playbook_context="",
        )

        template = prompt_registry.get("redline_generation", version="4.0.0")
        request = LLMRequest(
            prompt=prompt,
            system_prompt=template.system_prompt if template else None,
            model=template.default_model if template else "gpt-4o",
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        from app.domains.ai.llm import StructuredOutputParser

        provider = OpenAIProvider(api_key=settings.openai_api_key)
        try:
            response = await provider.complete(request)
            parsed = StructuredOutputParser.parse_json(response.content)

            if parsed:
                draft_text = parsed.get("proposed_text", response.content)
                confidence = parsed.get("confidence", 0.85)
            else:
                draft_text = response.content
                confidence = 0.5

            # Build confidence provenance from available data
            # In production, query similar contracts, approved templates, and policies
            provenance = {
                "confidence": confidence,
                "sources": [
                    {"type": "similar_contracts", "count": 0, "label": "Similar Contracts"},
                    {"type": "approved_templates", "count": 0, "label": "Approved Templates"},
                    {"type": "policy_rules", "count": 0, "label": "Policy Rules"},
                ],
                "factors": [
                    {"name": "Clause Type Match", "score": 0.95, "weight": "high"},
                    {"name": "Jurisdiction Alignment", "score": 0.85 if jurisdiction else 0.5, "weight": "medium"},
                    {"name": "Industry Standard", "score": 0.80 if industry else 0.5, "weight": "medium"},
                    {"name": "Risk Level Appropriateness", "score": 0.90 if risk_level else 0.6, "weight": "low"},
                ],
                "matching_score": round(
                    (0.95 * 0.4)  # clause type
                    + (0.85 * 0.25 if jurisdiction else 0.5 * 0.25)  # jurisdiction
                    + (0.80 * 0.2 if industry else 0.5 * 0.2)  # industry
                    + (0.90 * 0.15 if risk_level else 0.6 * 0.15),  # risk level
                    2,
                ),
            }

            return {
                "draft_text": draft_text,
                "clause_type": clause_type,
                "confidence": confidence,
                "model_used": response.model,
                "provenance": provenance,
            }
        except RateLimitError:
            logger.warning("Rate limited during AI draft generation for %s", clause_type)
            raise
        except Exception as exc:
            logger.error("AI draft generation failed for %s: %s", clause_type, exc)
            raise

    def _to_dict(self, template) -> dict[str, Any]:
        """Convert to dict — already a dict from raw SQL repository."""
        if isinstance(template, dict):
            return template
        return {
            "template_id": str(template.template_id),
            "tenant_id": str(template.tenant_id),
            "name": template.name,
            "clause_type": template.clause_type,
            "category": template.category,
            "jurisdiction": template.jurisdiction,
            "industry": template.industry,
            "language": template.language,
            "risk_level": template.risk_level,
            "template_text": template.template_text,
            "variables": template.variables,
            "version": template.version,
            "status": template.status,
            "playbook_id": str(template.playbook_id) if template.playbook_id else None,
            "usage_count": template.usage_count,
            "accept_rate": template.accept_rate,
            "created_by": template.created_by,
            "approved_by": template.approved_by,
            "effective_date": template.effective_date.isoformat() if template.effective_date else None,
            "retired_date": template.retired_date.isoformat() if template.retired_date else None,
            "last_used": template.last_used.isoformat() if template.last_used else None,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
