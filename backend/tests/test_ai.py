"""Tests for AI analysis runtime — structured output parsing, prompt rendering, and schema validation."""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError
from app.domains.ai.llm import StructuredOutputParser, OpenAIProvider
from app.domains.ai.schemas import (
    AnalysisResult, RiskFinding, RedlineSuggestion,
    AnalysisRequest, AnalysisStatusResponse,
    AIReviewCopilotRequest, AIReviewCopilotResponse,
    AIReviewFeedbackRequest, AIReviewFeedbackResponse,
)
from app.domains.ai.prompts import prompt_registry


class TestStructuredOutputParsing:
    """Verify JSON extraction from LLM responses."""

    def test_parse_valid_json(self):
        content = '{"risk_score": 0.85, "findings": []}'
        parsed = StructuredOutputParser.parse_json(content)
        assert parsed is not None
        assert parsed["risk_score"] == 0.85

    def test_parse_json_from_code_block(self):
        content = 'Some text\n```json\n{"risk_score": 0.75}\n```\nmore text'
        parsed = StructuredOutputParser.parse_json(content)
        assert parsed is not None
        assert parsed["risk_score"] == 0.75

    def test_parse_json_with_extra_text(self):
        content = 'Here is the analysis:\n{"risk_score": 0.9, "summary": "High risk"}\nEnd.'
        parsed = StructuredOutputParser.parse_json(content)
        assert parsed is not None
        assert parsed["risk_score"] == 0.9

    def test_parse_malformed_json_returns_none(self):
        content = "This is not JSON at all"
        parsed = StructuredOutputParser.parse_json(content)
        assert parsed is None

    def test_confidence_calculation(self):
        assert StructuredOutputParser.calculate_confidence({"key": "val"}, None) == 0.5
        assert StructuredOutputParser.calculate_confidence(None, None) == 0.0


class TestAnalysisSchemas:
    """Verify Pydantic schema validation for AI outputs."""

    def test_valid_risk_finding(self):
        finding = RiskFinding(
            clause_type="indemnification",
            severity="high",
            title="Uncapped liability",
            description="The clause exposes unlimited liability",
            recommendation="Add cap of $1M",
            confidence=0.85,
            risk_score=0.8,
        )
        assert finding.severity == "high"
        assert finding.confidence == 0.85

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            RiskFinding(
                clause_type="test", severity="invalid",
                title="Test", description="Test",
            )

    def test_confidence_range_enforced(self):
        with pytest.raises(ValidationError):
            RiskFinding(
                clause_type="test", severity="high",
                title="Test", description="Test",
                confidence=1.5,
            )

    def test_valid_redline_suggestion(self):
        redline = RedlineSuggestion(
            clause_type="liability",
            original_text="Old text",
            proposed_text="New text",
            rationale="Better protection",
            risk_level="high",
            confidence=0.8,
        )
        assert redline.proposed_text == "New text"

    def test_analysis_result_build(self):
        result = AnalysisResult(
            risk_score=0.75,
            summary="High risk contract",
            findings=[
                RiskFinding(clause_type="indemnification", severity="critical",
                            title="Risk", description="Description", confidence=0.9),
            ],
        )
        assert result.risk_score == 0.75
        assert len(result.findings) == 1

    def test_analysis_request_validation(self):
        req = AnalysisRequest(upload_id="test-uuid", analysis_type="full")
        assert req.analysis_type == "full"

    def test_invalid_analysis_type_rejected(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(upload_id="test", analysis_type="invalid")

    def test_review_copilot_request_validation(self):
        request = AIReviewCopilotRequest(
            review_id="review-123",
            prompt="Please summarize the highest-risk items.",
            max_suggestions=2,
        )
        assert request.review_id == "review-123"
        assert request.max_suggestions == 2

    def test_review_copilot_feedback_validation(self):
        feedback = AIReviewFeedbackRequest(
            review_id="review-123",
            suggestion_id="sugg-1",
            helpful=True,
            feedback="The recommendation was accurate and useful.",
        )
        assert feedback.helpful is True


class TestPromptTemplates:
    """Verify prompt template registration and rendering."""

    def test_risk_analysis_prompt_exists(self):
        template = prompt_registry.get("risk_analysis")
        assert template is not None
        assert template.key == "risk_analysis"
        assert template.version == 1

    def test_redline_prompt_exists(self):
        template = prompt_registry.get("redline_generation")
        assert template is not None

    def test_prompt_rendering(self):
        text = prompt_registry.render(
            "risk_analysis", version=1,
            chunks=[{"text": "Test clause", "page_numbers": [1]}],
        )
        assert "Test clause" in text
        assert "risk_score" in text

    def test_missing_prompt_raises(self):
        with pytest.raises(ValueError):
            prompt_registry.render("nonexistent_prompt")


class TestProviderAbstraction:
    """Verify LLM provider interface."""

    def test_openai_provider_attributes(self):
        provider = OpenAIProvider(api_key="test")
        assert provider.provider_name == "openai"
        assert "gpt-4o" in provider.supported_models

    def test_cost_estimation(self):
        provider = OpenAIProvider(api_key="test")
        cost = provider._estimate_cost("gpt-4o", 1000, 200)
        assert cost > 0
        assert cost < 1.0


class TestTenantIsolation:
    """Verify AI models have tenant fields."""

    def test_execution_run_has_tenant(self):
        from app.domains.ai.models import AIExecutionRun
        assert hasattr(AIExecutionRun, "tenant_id")

    def test_finding_has_tenant(self):
        from app.domains.ai.models import AIFinding
        assert hasattr(AIFinding, "tenant_id")

    def test_redline_has_tenant(self):
        from app.domains.ai.models import AIRedline
        assert hasattr(AIRedline, "tenant_id")
