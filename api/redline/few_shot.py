"""Few-shot examples for redline prompt templates.

Provides 3 curated few-shot examples per clause type showing good vs.
bad redline suggestions. Each example demonstrates proper legal analysis,
commercially reasonable proposed language, and clear rationale.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import ClauseType

logger = logging.getLogger(__name__)


@dataclass
class FewShotExample:
    """A single few-shot example for redline generation.

    Shows an original clause, a poor (bad) redline to avoid, and a
    good (recommended) redline with rationale.
    """

    clause_type: ClauseType
    title: str
    scenario: str
    original_clause: str
    bad_redline: Dict[str, Any]
    good_redline: Dict[str, Any]
    key_lessons: List[str]


class FewShotExamples:
    """Curated few-shot examples for redline prompt engineering.

    Contains 3 examples per clause type (24 total) demonstrating
    the difference between legally dangerous and high-quality redline
    suggestions. Used to guide LLM output toward better quality.

    Usage:
        examples = FewShotExamples()
        liability_examples = examples.get_examples(ClauseType.LIABILITY_CAPS)
        all_examples = examples.get_all_examples()
    """

    def __init__(self) -> None:
        """Initialize all few-shot examples."""
        self._examples: Dict[ClauseType, List[FewShotExample]] = {}
        self._initialize_all()

    def _initialize_all(self) -> None:
        """Build examples for all 8 clause types."""
        self._examples[ClauseType.LIABILITY_CAPS] = self._liability_caps_examples()
        self._examples[ClauseType.INDEMNIFICATION] = self._indemnification_examples()
        self._examples[ClauseType.IP_OWNERSHIP] = self._ip_ownership_examples()
        self._examples[ClauseType.PAYMENT_TERMS] = self._payment_terms_examples()
        self._examples[ClauseType.GOVERNING_LAW] = self._governing_law_examples()
        self._examples[ClauseType.TERMINATION_RIGHTS] = self._termination_examples()
        self._examples[ClauseType.CONFIDENTIALITY] = self._confidentiality_examples()
        self._examples[ClauseType.FORCE_MAJEURE] = self._force_majeure_examples()

    def get_examples(self, clause_type: ClauseType) -> List[FewShotExample]:
        """Get few-shot examples for a specific clause type.

        Args:
            clause_type: The clause type to retrieve examples for.

        Returns:
            List of FewShotExample objects.
        """
        return list(self._examples.get(clause_type, []))

    def get_all_examples(self) -> Dict[ClauseType, List[FewShotExample]]:
        """Get all few-shot examples across all clause types.

        Returns:
            Dict mapping clause types to their example lists.
        """
        return dict(self._examples)

    def get_examples_for_prompt(
        self, clause_type: ClauseType, max_examples: int = 3
    ) -> List[Dict[str, Any]]:
        """Get formatted examples suitable for prompt injection.

        Args:
            clause_type: The clause type to get examples for.
            max_examples: Maximum number of examples to return.

        Returns:
            List of formatted example dicts with 'original', 'bad', 'good' keys.
        """
        examples = self.get_examples(clause_type)[:max_examples]
        return [
            {
                "scenario": ex.scenario,
                "original_clause": ex.original_clause,
                "bad_redline": ex.bad_redline,
                "good_redline": ex.good_redline,
                "key_lessons": ex.key_lessons,
            }
            for ex in examples
        ]

    # ── Liability Caps Examples ──────────────────────────────────────────────

    def _liability_caps_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.LIABILITY_CAPS,
                title="SaaS Services Agreement — Zero Liability Cap",
                scenario="Enterprise SaaS deal, $500K annual contract value, buyer is a financial services firm",
                original_clause=(
                    "IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER FOR ANY "
                    "INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. "
                    "THE TOTAL LIABILITY OF EITHER PARTY SHALL NOT EXCEED $0."
                ),
                bad_redline={
                    "proposed_text": (
                        "IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER FOR ANY "
                        "DAMAGES WHATSOEVER. THE TOTAL LIABILITY OF EITHER PARTY SHALL "
                        "NOT EXCEED THE FEES PAID IN THE PRECEDING 12 MONTHS."
                    ),
                    "rationale": "Removed the zero cap but kept an overly broad damages waiver.",
                    "issues": [
                        "Still waives all damages without carve-outs",
                        "No exclusion for fraud, IP infringement, or confidentiality breach",
                        "Does not address data breach liability for financial services",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "EXCLUSIONS: Nothing in this Section shall limit either party's liability "
                        "for (a) fraud or willful misconduct; (b) death or personal injury caused "
                        "by its negligence; (c) breach of its confidentiality obligations under "
                        "Section [X]; (d) breach of its indemnification obligations under Section "
                        "[Y]; (e) infringement of the other party's intellectual property rights; "
                        "or (f) amounts payable under Section [Z] (Payment Terms).\n\n"
                        "LIMITATION OF LIABILITY: EXCEPT FOR THE EXCLUSIONS SET FORTH ABOVE, "
                        "NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, "
                        "SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. EXCEPT FOR THE EXCLUSIONS "
                        "SET FORTH ABOVE, EACH PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF "
                        "OR RELATED TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, "
                        "SHALL NOT EXCEED THE TOTAL FEES PAID BY CLIENT TO PROVIDER DURING THE "
                        "12 MONTHS IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO THE CLAIM."
                    ),
                    "rationale": (
                        "Properly structured liability cap with essential carve-outs for fraud, "
                        "IP infringement, confidentiality, and indemnification. The cap is tied "
                        "to 12 months of fees, which is market standard for SaaS. The damages "
                        "waiver properly excludes the carve-outs from its scope."
                    ),
                    "confidence": 0.92,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "A $0 liability cap is a red flag — always add a reasonable cap with carve-outs",
                    "Carve-outs for fraud, IP, confidentiality, and indemnification are essential",
                    "The damages waiver must explicitly exclude the carve-out categories",
                    "Cap tied to fees paid (1x-3x) is market standard for services agreements",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.LIABILITY_CAPS,
                title="Professional Services — Unlimited Liability for Everything",
                scenario="IT consulting agreement, $2M project, consultant's standard terms",
                original_clause=(
                    "Consultant shall be liable for all losses, damages, claims, and expenses "
                    "arising out of or relating to the Services, regardless of the cause or "
                    "the theory of liability."
                ),
                bad_redline={
                    "proposed_text": (
                        "Consultant's liability shall be limited to the fees paid for the "
                        "specific service giving rise to the claim."
                    ),
                    "rationale": "Cap is too narrow and doesn't address the scope of liability.",
                    "issues": [
                        "Does not cap total aggregate liability",
                        "No exclusion for gross negligence or willful misconduct",
                        "No consequential damages waiver",
                        "Per-service cap is impractical for multi-service engagements",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "LIMITATION OF LIABILITY. EXCEPT FOR (i) fraud or willful misconduct; "
                        "(ii) death or personal injury; (iii) breach of confidentiality; "
                        "(iv) indemnification obligations; and (v) infringement of intellectual "
                        "property rights (collectively, the 'Carve-Outs'):\n\n"
                        "(a) NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, "
                        "INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.\n\n"
                        "(b) EACH PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED "
                        "TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, SHALL "
                        "NOT EXCEED THE TOTAL FEES PAID OR PAYABLE BY CLIENT TO CONSULTANT "
                        "UNDER THIS AGREEMENT.\n\n"
                        "(c) THE CARVE-OUTS SHALL NOT BE SUBJECT TO THE FOREGOING LIMITATIONS."
                    ),
                    "rationale": (
                        "Standard mutual liability cap with proper carve-outs. The cap is set at "
                        "total contract value (fees paid/payable), which is appropriate for a "
                        "defined-scope consulting project. The consequential damages waiver is "
                        "mutual and the carve-outs are comprehensive."
                    ),
                    "confidence": 0.88,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Unlimited liability is not commercially reasonable for services agreements",
                    "Always include a mutual cap with standard carve-outs",
                    "The cap amount should relate to the contract value",
                    "Consequential damages waivers should be mutual",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.LIABILITY_CAPS,
                title="Indemnification Carve-Out Dispute",
                scenario="Technology licensing deal, $10M deal size, licensor's form",
                original_clause=(
                    "The limitation of liability set forth in this Section X shall not apply "
                    "to either party's indemnification obligations under Section Y."
                ),
                bad_redline={
                    "proposed_text": (
                        "The limitation of liability shall apply to all claims, including "
                        "indemnification claims."
                    ),
                    "rationale": "Removes the indemnification carve-out entirely.",
                    "issues": [
                        "Indemnification is a risk allocation mechanism — capping it defeats its purpose",
                        "IP indemnification should never be subject to a general liability cap",
                        "This would leave client exposed to uncapped infringement damages by the other party",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "The limitations of liability set forth in this Section X shall not apply to: "
                        "(a) either party's indemnification obligations under Section Y; "
                        "(b) breach of confidentiality under Section Z; (c) fraud or willful "
                        "misconduct; (d) infringement of the other party's intellectual property "
                        "rights; (e) amounts payable as fees or expenses under this Agreement; "
                        "and (f) violations of applicable law. For the avoidance of doubt, "
                        "indemnification claims for third-party IP infringement shall not be "
                        "subject to any cap on liability."
                    ),
                    "rationale": (
                        "Properly preserves essential carve-outs from the liability cap. "
                        "Indemnification is a risk transfer mechanism that should not be capped. "
                        "The clause also adds clarity by listing all carve-outs in one place."
                    ),
                    "confidence": 0.95,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Indemnification obligations should generally be excluded from liability caps",
                    "IP infringement indemnification should never be capped",
                    "List all carve-outs explicitly to avoid ambiguity",
                    "Some carve-outs (like fees) are standard and expected",
                ],
            ),
        ]

    # ── Indemnification Examples ─────────────────────────────────────────────

    def _indemnification_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.INDEMNIFICATION,
                title="One-Sided Indemnification with No Cap",
                scenario="Managed services agreement, $3M annual contract, service provider's form",
                original_clause=(
                    "Service Provider shall indemnify, defend, and hold harmless Client from "
                    "and against any and all claims, losses, damages, liabilities, costs, and "
                    "expenses (including reasonable attorneys' fees) arising out of or relating "
                    "to this Agreement."
                ),
                bad_redline={
                    "proposed_text": (
                        "Client shall indemnify, defend, and hold harmless Service Provider from "
                        "and against any and all claims arising out of or relating to this Agreement."
                    ),
                    "rationale": "Simply flipped the indemnity from provider to client without addressing scope.",
                    "issues": [
                        "Still one-sided, just reversed",
                        "No limitation on scope — 'arising out of or relating to' is extremely broad",
                        "No exclusion for client's own negligence",
                        "No cap on indemnification amount",
                        "No control of defense provisions",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Mutual Indemnification.\n\n"
                        "(a) Indemnification by Service Provider. Service Provider shall indemnify, "
                        "defend, and hold harmless Client from and against any third-party claims, "
                        "losses, damages, and expenses (including reasonable attorneys' fees) to the "
                        "extent arising out of or resulting from (i) Service Provider's gross negligence "
                        "or willful misconduct; (ii) Service Provider's breach of this Agreement; or "
                        "(iii) a claim that the Services infringe a third party's intellectual "
                        "property rights.\n\n"
                        "(b) Indemnification by Client. Client shall indemnify, defend, and hold "
                        "harmless Service Provider from and against any third-party claims, losses, "
                        "damages, and expenses (including reasonable attorneys' fees) to the extent "
                        "arising out of or resulting from (i) Client's gross negligence or willful "
                        "misconduct; (ii) Client's breach of this Agreement; or (iii) Client's use "
                        "of the Services in violation of applicable law or the Agreement.\n\n"
                        "(c) Control of Defense. The indemnifying party shall have the right to "
                        "assume the defense of any indemnified claim with counsel reasonably "
                        "acceptable to the indemnified party. The indemnified party shall have the "
                        "right to participate in the defense at its own expense. The indemnifying "
                        "party shall not settle any claim without the indemnified party's prior "
                        "written consent, which shall not be unreasonably withheld."
                    ),
                    "rationale": (
                        "Mutual indemnification with clearly scoped obligations. Each party indemnifies "
                        "the other for claims arising from their own fault. IP infringement indemnity "
                        "is properly included for the service provider. Control of defense provisions "
                        "are balanced and market standard."
                    ),
                    "confidence": 0.90,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Indemnification should be mutual, not one-sided",
                    "Scope should be tied to each party's fault or breach",
                    "IP infringement indemnification is critical for service/technology providers",
                    "Control of defense and settlement consent provisions are essential",
                    "Always include a 'proportionate' or 'to the extent arising from' limitation",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.INDEMNIFICATION,
                title="No Duty to Defend — Indemnification Only",
                scenario="Software license agreement, buyer's form heavily favoring licensee",
                original_clause=(
                    "Licensor shall indemnify Licensee for any damages awarded by a court of "
                    "competent jurisdiction in connection with a third-party claim of IP infringement."
                ),
                bad_redline={
                    "proposed_text": (
                        "Licensor shall indemnify Licensee for any losses incurred in connection "
                        "with a third-party claim."
                    ),
                    "rationale": "Still no duty to defend and scope is vague.",
                    "issues": [
                        "No duty to defend — licensee bears defense costs up front",
                        "'Losses incurred' is vague and could be contested",
                        "No control of defense provisions",
                        "No obligation to reimburse defense costs",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "IP Indemnification.\n\n"
                        "(a) Licensor shall defend, indemnify, and hold harmless Licensee and its "
                        "affiliates, officers, directors, and employees from and against any third-party "
                        "claim alleging that the Licensed Software infringes any patent, copyright, "
                        "trade secret, or other intellectual property right of such third party, "
                        "including all liabilities, losses, damages, costs, and expenses (including "
                        "reasonable attorneys' fees and costs of defense) incurred by the indemnified "
                        "parties.\n\n"
                        "(b) If the Licensed Software becomes, or in Licensor's opinion is likely to "
                        "become, the subject of an infringement claim, Licensor may, at its option "
                        "and expense: (i) procure the right for Licensee to continue using the "
                        "Licensed Software; (ii) modify the Licensed Software to make it "
                        "non-infringing while maintaining substantially equivalent functionality; "
                        "or (iii) if (i) and (ii) are not commercially reasonable, terminate the "
                        "license and refund the fees paid for the infringing portion.\n\n"
                        "(c) Licensor shall have no obligation under this Section to the extent the "
                        "claim arises from (i) Licensee's modification of the Licensed Software; "
                        "(ii) combination of the Licensed Software with products not provided by "
                        "Licensor; or (iii) Licensee's use of the Licensed Software in violation "
                        "of this Agreement or applicable law."
                    ),
                    "rationale": (
                        "Comprehensive IP indemnification with duty to defend, proper scope, "
                        "and mitigation options for the licensor. The exclusion for modifications "
                        "and combinations is standard and protects the licensor from liability for "
                        "licensee-caused infringement."
                    ),
                    "confidence": 0.93,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Always include a duty to defend, not just indemnify",
                    "IP indemnification should cover attorneys' fees and defense costs",
                    "Include mitigation options for the indemnifying party",
                    "Standard exclusions for modifications and combinations are appropriate",
                    "The indemnity should extend to affiliates and downstream users",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.INDEMNIFICATION,
                title="Sole Control of Defense with No Consent Right",
                scenario="Outsourcing agreement, customer's form with aggressive terms",
                original_clause=(
                    "Service Provider shall indemnify Customer. Service Provider shall have sole "
                    "control of the defense and settlement of any claim."
                ),
                bad_redline={
                    "proposed_text": (
                        "Customer shall have sole control of the defense and settlement of any claim."
                    ),
                    "rationale": "Simply reversed control without addressing the balance.",
                    "issues": [
                        "If customer controls defense but provider pays, provider has no say in costs",
                        "No consent requirement for settlements",
                        "Could lead to unreasonable defense costs being passed to provider",
                        "No mechanism for resolving conflicts of interest",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Control of Defense.\n\n"
                        "(a) The indemnifying party shall have the right, at its own expense, to "
                        "assume the defense of any claim with counsel reasonably acceptable to the "
                        "indemnified party.\n\n"
                        "(b) The indemnified party shall have the right to participate in the defense "
                        "at its own expense.\n\n"
                        "(c) The indemnifying party shall not settle any claim without the indemnified "
                        "party's prior written consent, which shall not be unreasonably withheld or "
                        "delayed. The indemnifying party may settle a claim without the indemnified "
                        "party's consent if the settlement (i) involves no finding or admission of "
                        "wrongdoing by the indemnified party; (ii) includes a full release of the "
                        "indemnified party; and (iii) imposes no ongoing obligations on the "
                        "indemnified party.\n\n"
                        "(d) If the indemnifying party assumes the defense, the indemnified party "
                        "shall cooperate in good faith and make available relevant information and "
                        "personnel at the indemnifying party's reasonable request."
                    ),
                    "rationale": (
                        "Balanced control of defense provisions. The indemnifying party (paying) "
                        "gets to control the defense, but the indemnified party has participation "
                        "rights and consent over settlements. The settlement without consent "
                        "provision is a market-standard compromise that allows efficient resolution."
                    ),
                    "confidence": 0.91,
                    "attorney_review_required": False,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "The party paying for defense should generally control it",
                    "The indemnified party must have settlement consent rights",
                    "Include a 'clean settlement' exception for settlements without admission of liability",
                    "Cooperation obligations protect both parties",
                    "Counsel must be reasonably acceptable to both sides",
                ],
            ),
        ]

    # ── IP Ownership Examples ────────────────────────────────────────────────

    def _ip_ownership_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.IP_OWNERSHIP,
                title="Work-for-Hire Without Assignment of Pre-existing IP",
                scenario="Software development agreement, $500K project, client form",
                original_clause=(
                    "All work product created by Developer under this Agreement shall be "
                    "considered work made for hire and shall be owned exclusively by Client."
                ),
                bad_redline={
                    "proposed_text": (
                        "All work product created by Developer under this Agreement shall be owned "
                        "by Client. Developer retains ownership of all pre-existing tools and "
                        "methodologies."
                    ),
                    "rationale": "Recognizes pre-existing IP but doesn't grant a license back to client.",
                    "issues": [
                        "No license grant for pre-existing IP incorporated into deliverables",
                        "No warranty that pre-existing IP can be used for client's benefit",
                        "No definition of 'pre-existing tools and methodologies'",
                        "No representation that deliverables don't infringe third-party IP",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Ownership.\n\n"
                        "(a) Foreground IP. All deliverables, software, documentation, and other "
                        "work product created by Developer specifically for Client under this "
                        "Agreement ('Foreground IP') shall be owned exclusively by Client. To the "
                        "extent any Foreground IP does not qualify as a 'work made for hire' under "
                        "applicable law, Developer hereby irrevocably assigns to Client all right, "
                        "title, and interest in and to such Foreground IP.\n\n"
                        "(b) Background IP. Developer retains all right, title, and interest in and "
                        "to any pre-existing tools, libraries, methodologies, and intellectual "
                        "property owned by Developer prior to this Agreement or developed "
                        "independently of this Agreement ('Background IP').\n\n"
                        "(c) License to Background IP. Developer hereby grants to Client a perpetual, "
                        "irrevocable, worldwide, royalty-free, fully paid-up, non-exclusive license "
                        "to use, reproduce, modify, and create derivative works of any Background "
                        "IP incorporated into the Foreground IP, solely as necessary for Client's "
                        "use and enjoyment of the Foreground IP.\n\n"
                        "(d) Moral Rights. To the extent permitted by law, Developer waives any "
                        "moral rights in the Foreground IP."
                    ),
                    "rationale": (
                        "Properly distinguishes foreground from background IP. Includes express "
                        "assignment for non-work-for-hire elements, a license-back for background IP, "
                        "and moral rights waiver. This protects both parties: client gets full "
                        "ownership of what they're paying for, and developer retains their core tools."
                    ),
                    "confidence": 0.94,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Always distinguish foreground (new) IP from background (pre-existing) IP",
                    "Work-for-hire alone is insufficient — add express assignment language",
                    "Include a license grant for background IP incorporated into deliverables",
                    "Moral rights waivers are important in many jurisdictions",
                    "Define terms clearly to avoid disputes over scope",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.IP_OWNERSHIP,
                title="Joint Ownership Without Accounting",
                scenario="Joint development agreement, 50/50 cost share, no IP plan",
                original_clause=(
                    "All intellectual property developed under this Agreement shall be jointly "
                    "owned by both parties."
                ),
                bad_redline={
                    "proposed_text": (
                        "All intellectual property developed under this Agreement shall be jointly "
                        "owned by both parties. Each party may use and license the IP without the "
                        "other's consent."
                    ),
                    "rationale": "Joint ownership without accounting creates significant risk.",
                    "issues": [
                        "Under US copyright law, joint owners can license without accounting",
                        "Under patent law, joint owners may need to account for profits",
                        "No mechanism for prosecution or maintenance of IP rights",
                        "No dispute resolution for deadlock situations",
                        "No allocation of prosecution costs",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Joint Ownership.\n\n"
                        "(a) All intellectual property developed jointly by the parties under this "
                        "Agreement ('Joint IP') shall be jointly owned by both parties.\n\n"
                        "(b) Each party shall have the right to practice, use, and exploit the Joint "
                        "IP without the consent of or accounting to the other party, subject to the "
                        "confidentiality obligations of this Agreement.\n\n"
                        "(c) Neither party may grant third-party licenses or sublicenses to the Joint "
                        "IP without the prior written consent of the other party, such consent not "
                        "to be unreasonably withheld.\n\n"
                        "(d) The parties shall mutually agree on a strategy for patent prosecution "
                        "and maintenance of Joint IP, with costs shared equally. If the parties "
                        "cannot agree, either party may file in its own name and bear the costs, "
                        "with the other party retaining an undivided interest.\n\n"
                        "(e) Each party shall promptly disclose to the other all Joint IP and shall "
                        "cooperate in the preparation, filing, and prosecution of patent applications."
                    ),
                    "rationale": (
                        "Properly structured joint ownership that balances both parties' interests. "
                        "Each party can use the IP internally without restriction, but third-party "
                        "licensing requires mutual consent. Patent prosecution and cost allocation "
                        "are addressed, preventing deadlock."
                    ),
                    "confidence": 0.87,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Joint ownership is complex — avoid if possible, structure carefully if necessary",
                    "Restrict third-party licensing rights to prevent one party from undermining the other",
                    "Address patent prosecution, maintenance, and cost allocation",
                    "Include disclosure and cooperation obligations",
                    "Consider jurisdiction-specific rules on joint ownership",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.IP_OWNERSHIP,
                title="Improvement Clauses — Capturing Future IP",
                scenario="Long-term technology partnership, vendor's form with broad improvement clause",
                original_clause=(
                    "All improvements, enhancements, modifications, and derivatives of the Software "
                    "shall be owned exclusively by Vendor."
                ),
                bad_redline={
                    "proposed_text": (
                        "All improvements, enhancements, modifications, and derivatives of the "
                        "Software shall be jointly owned by the parties."
                    ),
                    "rationale": "Still too broad — captures independently developed improvements.",
                    "issues": [
                        "'Improvements' and 'enhancements' are vague and could capture independently developed IP",
                        "No exclusion for improvements developed without use of vendor's software",
                        "Could discourage client from investing in their own R&D",
                        "No field-of-use restrictions",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Improvements.\n\n"
                        "(a) Improvements to the Software that are developed specifically for and "
                        "funded by Client under a mutually agreed statement of work ('Client-Specific "
                        "Improvements') shall be owned by Client, subject to Vendor's license rights "
                        "under Section (c).\n\n"
                        "(b) Improvements that are of general applicability and developed by Vendor "
                        "at its own expense, including those arising from Client-Specific Improvements "
                        "that Vendor generalizes ('Vendor Improvements'), shall be owned by Vendor.\n\n"
                        "(c) Vendor grants Client a perpetual, irrevocable, worldwide, royalty-free "
                        "license to any Vendor Improvements that are incorporated into the Software "
                        "during the term of this Agreement.\n\n"
                        "(d) For the avoidance of doubt, neither party shall have any obligation to "
                        "disclose or assign to the other any intellectual property developed "
                        "independently and without use of the other party's confidential information."
                    ),
                    "rationale": (
                        "Fairly allocates ownership of improvements based on who funded and developed them. "
                        "Client pays for customization gets ownership; vendor's general R&D remains theirs. "
                        "The license-back ensures client benefits from vendor improvements to their software."
                    ),
                    "confidence": 0.89,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Improvement clauses should be scoped to what each party actually develops",
                    "Client-funded customizations should belong to the client",
                    "Vendor's general improvements should remain with vendor with license to client",
                    "Avoid broad language that could capture independently developed IP",
                    "Include a 'for the avoidance of doubt' provision for independent development",
                ],
            ),
        ]

    # ── Payment Terms Examples ───────────────────────────────────────────────

    def _payment_terms_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.PAYMENT_TERMS,
                title="Auto-Renewal Without Notice",
                scenario="SaaS subscription agreement, $120K/year, vendor's standard form",
                original_clause=(
                    "This Agreement shall automatically renew for successive one-year terms "
                    "unless either party provides notice of non-renewal at least 30 days prior "
                    "to the end of the then-current term."
                ),
                bad_redline={
                    "proposed_text": (
                        "This Agreement shall automatically renew for successive one-year terms "
                        "unless Client provides notice of non-renewal at least 90 days prior."
                    ),
                    "rationale": "Extended notice period but still one-sided and no price protection.",
                    "issues": [
                        "Only client can prevent renewal — vendor has no obligation to remind",
                        "No price escalation cap on renewal",
                        "90 days is longer than standard (30-60 days)",
                        "No obligation to provide renewal pricing in advance",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Term and Renewal.\n\n"
                        "(a) Initial Term. This Agreement shall commence on the Effective Date and "
                        "continue for an initial term of [one (1) year] (the 'Initial Term').\n\n"
                        "(b) Renewal. Following the Initial Term, this Agreement shall automatically "
                        "renew for successive [one (1) year] renewal terms (each, a 'Renewal Term'), "
                        "unless either party provides written notice of non-renewal at least [sixty (60)] "
                        "days prior to the end of the then-current term.\n\n"
                        "(c) Renewal Pricing. Vendor shall provide Client with written notice of any "
                        "price increases for the upcoming Renewal Term at least [ninety (90)] days "
                        "prior to the start of such Renewal Term. Any price increase shall not exceed "
                        "[five percent (5%)] over the pricing for the preceding term. If Client does "
                        "not accept the price increase, Client may terminate this Agreement without "
                        "penalty upon written notice within [thirty (30)] days of receiving the "
                        "renewal pricing notice.\n\n"
                        "(d) Non-Renewal Notice. Vendor shall send a reminder notice to Client "
                        "regarding upcoming renewal at least [forty-five (45)] days prior to the "
                        "non-renewal deadline."
                    ),
                    "rationale": (
                        "Balanced renewal provisions that protect both parties. Client gets advance "
                        "notice of price increases with a cap and termination right. Vendor gets "
                        "automatic renewal with reasonable notice. The reminder notice prevents "
                        "inadvertent non-renewal."
                    ),
                    "confidence": 0.90,
                    "attorney_review_required": False,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Auto-renewal should be mutual — either party can prevent it",
                    "Include price escalation caps and advance notice of increases",
                    "Give client a termination right if they don't accept price increases",
                    "Reminder notices prevent disputes about inadvertent renewals",
                    "Notice periods of 30-60 days are market standard",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.PAYMENT_TERMS,
                title="Unilateral Setoff Rights",
                scenario="Professional services agreement, client's form with broad setoff",
                original_clause=(
                    "Client may set off against any amounts payable to Consultant any amounts "
                    "that Client claims are owed by Consultant."
                ),
                bad_redline={
                    "proposed_text": (
                        "Neither party may set off any amounts against amounts payable to the "
                        "other party."
                    ),
                    "rationale": "Removes setoff entirely, which may be too restrictive for client.",
                    "issues": [
                        "No setoff rights at all — even for undisputed amounts",
                        "Forces separate litigation for related claims",
                        "May be commercially unreasonable if consultant clearly owes money",
                        "No mechanism for disputed amounts",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Setoff.\n\n"
                        "(a) Either party may set off against amounts payable to the other party "
                        "any amounts that are undisputed and finally determined to be owed by the "
                        "other party under this Agreement.\n\n"
                        "(b) If a party disputes an amount owed in good faith, the disputing party "
                        "shall pay all undisputed amounts when due. The disputed amount shall be "
                        "resolved in accordance with the dispute resolution provisions of this "
                        "Agreement.\n\n"
                        "(c) Neither party may withhold payment of undisputed amounts pending "
                        "resolution of a good faith dispute."
                    ),
                    "rationale": (
                        "Balanced setoff provision that allows setoff for undisputed, finally "
                        "determined amounts while protecting both parties from abuse. The requirement "
                        "to pay undisputed amounts prevents a party from using setoff as leverage."
                    ),
                    "confidence": 0.88,
                    "attorney_review_required": False,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "One-sided setoff rights are a red flag — setoff should be mutual",
                    "Require payment of undisputed amounts even when there's a dispute",
                    "Setoff should only apply to finally determined amounts, not mere claims",
                    "Disputed amounts should go through the agreement's dispute resolution process",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.PAYMENT_TERMS,
                title="Late Payment Penalty — Usury Risk",
                scenario="Equipment lease agreement, 24% late fee with compounding",
                original_clause=(
                    "Late payments shall incur interest at the rate of 2% per month, compounded "
                    "monthly, or the maximum rate permitted by law, whichever is greater."
                ),
                bad_redline={
                    "proposed_text": (
                        "Late payments shall incur a flat fee of $500."
                    ),
                    "rationale": "Flat fee may be insufficient deterrent for large balances.",
                    "issues": [
                        "Flat fee doesn't scale with the overdue amount",
                        "No incentive for timely payment on large invoices",
                        "Doesn't compensate for time value of money",
                        "Could be challenged as an unenforceable penalty if disproportionate",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Late Payment.\n\n"
                        "(a) Any amount not paid when due shall bear interest at the rate of [one "
                        "and one-half percent (1.5%)] per month, or [eighteen percent (18%)] per "
                        "annum, whichever is lower, calculated from the due date through the date "
                        "of payment.\n\n"
                        "(b) In addition to interest, a late payment fee of [the lesser of (i) five "
                        "percent (5%) of the overdue amount or (ii) $500] may be charged for each "
                        "late payment.\n\n"
                        "(c) In no event shall the interest rate exceed the maximum rate permitted "
                        "by applicable law. If the rate specified exceeds the legal maximum, the "
                        "rate shall be reduced to such maximum.\n\n"
                        "(d) Interest shall be computed on a simple (not compounded) basis."
                    ),
                    "rationale": (
                        "Commercially reasonable late payment terms. The 1.5% monthly rate is market "
                        "standard and below most state usury limits. Simple interest avoids compounding "
                        "issues. The savings clause ensures legal compliance. The flat fee cap prevents "
                        "excessive charges."
                    ),
                    "confidence": 0.92,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Late payment interest of 1-1.5% per month is market standard",
                    "Always include a usury savings clause",
                    "Simple interest is preferred over compounding to avoid legal challenges",
                    "Flat late fees should be reasonable and proportionate",
                    "Consider state-specific usury limits (especially for consumer transactions)",
                ],
            ),
        ]

    # ── Governing Law Examples ───────────────────────────────────────────────

    def _governing_law_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.GOVERNING_LAW,
                title="Foreign Governing Law with No Local Presence",
                scenario="Services agreement, US-based client, foreign vendor's form with UK law",
                original_clause=(
                    "This Agreement shall be governed by and construed in accordance with the "
                    "laws of England and Wales. The parties submit to the exclusive jurisdiction "
                    "of the courts of London, England."
                ),
                bad_redline={
                    "proposed_text": (
                        "This Agreement shall be governed by the laws of the State of New York. "
                        "The parties submit to the exclusive jurisdiction of the courts of New "
                        "York County, New York."
                    ),
                    "rationale": "Changed to NY law but exclusive jurisdiction may still be inconvenient.",
                    "issues": [
                        "Exclusive jurisdiction in NY may be burdensome for a vendor in another state",
                        "No consideration of where services are performed",
                        "No arbitration alternative that might be more efficient",
                        "No waiver of inconvenient forum defense",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Governing Law and Jurisdiction.\n\n"
                        "(a) Governing Law. This Agreement and any disputes arising out of or "
                        "relating to this Agreement shall be governed by and construed in accordance "
                        "with the laws of the State of New York, without regard to its conflict of "
                        "laws principles. The United Nations Convention on Contracts for the "
                        "International Sale of Goods shall not apply.\n\n"
                        "(b) Exclusive Venue. Subject to Section (c), each party submits to the "
                        "exclusive jurisdiction of the federal and state courts located in New York "
                        "County, New York.\n\n"
                        "(c) Arbitration Option. Either party may, at its option, require that any "
                        "dispute arising out of or relating to this Agreement be resolved by binding "
                        "arbitration administered by JAMS under its Streamlined Arbitration Rules. "
                        "The arbitration shall be conducted in New York County, New York, or remotely "
                        "by video conference if the parties agree.\n\n"
                        "(d) Injunctive Relief. Notwithstanding the foregoing, either party may seek "
                        "injunctive or other equitable relief in any court of competent jurisdiction "
                        "to protect its intellectual property or confidential information."
                    ),
                    "rationale": (
                        "Provides NY governing law (favorable for US commercial contracts) with "
                        "an arbitration option for cost-effective dispute resolution. The CISG "
                        "exclusion is important for international transactions. The injunctive "
                        "relief carve-out protects IP rights."
                    ),
                    "confidence": 0.91,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Choose governing law that has well-developed commercial contract jurisprudence",
                    "Exclude CISG for cross-border US contracts",
                    "Consider arbitration as an alternative to litigation",
                    "Always include an injunctive relief carve-out for IP/confidentiality",
                    "Remote arbitration provisions are increasingly important",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.GOVERNING_LAW,
                title="Jury Trial Waiver in Consumer Context",
                scenario="Standard terms of service, B2B SaaS, vendor's form with jury waiver",
                original_clause=(
                    "Each party hereby irrevocably waives any and all right to trial by jury "
                    "in any legal proceeding arising out of or relating to this Agreement."
                ),
                bad_redline={
                    "proposed_text": (
                        "Each party hereby irrevocably waives any and all right to trial by jury."
                    ),
                    "rationale": "Same clause, just shortened. No context or exceptions.",
                    "issues": [
                        "Jury waivers may not be enforceable in some jurisdictions",
                        "No exception for fraud or willful misconduct",
                        "Doesn't address class action waiver enforceability",
                        "No severability clause for unenforceable provisions",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Waiver of Jury Trial.\n\n"
                        "(a) Each party acknowledges that any dispute arising out of or relating to "
                        "this Agreement is likely to be complex and is best resolved by a court "
                        "rather than a jury. Accordingly, to the extent permitted by applicable law "
                        "and subject to Section (b), each party irrevocably waives any and all right "
                        "to trial by jury in any proceeding arising out of or relating to this "
                        "Agreement.\n\n"
                        "(b) The waiver in Section (a) shall not apply to claims of fraud, willful "
                        "misconduct, or criminal activity.\n\n"
                        "(c) If the jury waiver in Section (a) is held to be unenforceable, the "
                        "parties agree that any trial shall be conducted by the court sitting "
                        "without a jury.\n\n"
                        "(d) This waiver has been knowingly and voluntarily made, and each party "
                        "acknowledges that it has been represented by counsel (or has had the "
                        "opportunity to be represented by counsel) in connection with this waiver."
                    ),
                    "rationale": (
                        "Properly drafted jury trial waiver with exceptions for fraud and willful "
                        "misconduct. Includes a fallback provision if the waiver is unenforceable. "
                        "The acknowledgment of knowing and voluntary waiver supports enforceability."
                    ),
                    "confidence": 0.85,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Jury trial waivers must be 'knowing and voluntary' to be enforceable",
                    "Include exceptions for fraud and willful misconduct",
                    "Add a fallback provision if the waiver is held unenforceable",
                    "Enforceability varies significantly by jurisdiction",
                    "B2B jury waivers are generally more enforceable than consumer waivers",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.GOVERNING_LAW,
                title="Multi-Tier Dispute Resolution — Unreasonable Timeframes",
                scenario="Long-term supply agreement, 30-day negotiation + 60-day mediation before litigation",
                original_clause=(
                    "Any dispute shall first be submitted to senior management for negotiation "
                    "(30 days), then to mediation (60 days), before either party may commence "
                    "litigation."
                ),
                bad_redline={
                    "proposed_text": (
                        "Any dispute shall first be submitted to senior management for negotiation "
                        "(90 days), then to mediation (120 days), before either party may commence "
                        "litigation."
                    ),
                    "rationale": "Extended timeframes but still no exceptions for urgent matters.",
                    "issues": [
                        "90+120 days is too long — could cause irreparable harm",
                        "No exception for IP infringement or confidentiality breaches",
                        "No exception for urgent injunctive relief",
                        "Could be used strategically to delay resolution",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Dispute Resolution.\n\n"
                        "(a) Negotiation. The parties shall attempt to resolve any dispute informally "
                        "through good faith negotiations between their respective senior management "
                        "representatives for a period of [thirty (30)] days.\n\n"
                        "(b) Mediation. If the dispute is not resolved through negotiation, either "
                        "party may submit the dispute to mediation administered by [JAMS/AAA] under "
                        "its mediation procedures. The mediation shall be completed within [sixty "
                        "(60)] days of submission.\n\n"
                        "(c) Litigation. If the dispute is not resolved through mediation, either "
                        "party may commence litigation.\n\n"
                        "(d) Exceptions. Notwithstanding the foregoing, either party may seek "
                        "injunctive or other equitable relief in any court of competent jurisdiction "
                        "without first complying with the negotiation or mediation requirements of "
                        "this Section, to the extent necessary to (i) protect its intellectual "
                        "property or confidential information; (ii) prevent irreparable harm; or "
                        "(iii) enforce its rights under the payment provisions of this Agreement.\n\n"
                        "(e) Tolling. The statute of limitations for any claim shall be tolled "
                        "during the negotiation and mediation periods."
                    ),
                    "rationale": (
                        "Balanced multi-tier dispute resolution with reasonable timeframes. The "
                        "injunctive relief exception is critical — it prevents the other party from "
                        "using the process to delay emergency relief. The tolling provision protects "
                        "both parties from statute of limitations issues."
                    ),
                    "confidence": 0.93,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Multi-tier dispute resolution should have reasonable, not excessive, timeframes",
                    "Always include an exception for injunctive relief",
                    "IP and confidentiality breaches need immediate access to courts",
                    "Include statute of limitations tolling during ADR periods",
                    "30 days negotiation + 60 days mediation is market standard",
                ],
            ),
        ]

    # ── Termination Rights Examples ──────────────────────────────────────────

    def _termination_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.TERMINATION_RIGHTS,
                title="Termination for Convenience — One-Sided",
                scenario="Marketing services agreement, client's form — client can terminate for convenience at any time",
                original_clause=(
                    "Client may terminate this Agreement at any time, for any reason or no reason, "
                    "upon 30 days written notice to Service Provider."
                ),
                bad_redline={
                    "proposed_text": (
                        "Either party may terminate this Agreement at any time, for any reason "
                        "or no reason, upon 30 days written notice."
                    ),
                    "rationale": "Made mutual but no protection for service provider's investment.",
                    "issues": [
                        "No early termination fees or wind-down costs",
                        "No protection for work already in progress",
                        "No compensation for committed resources",
                        "No transition assistance obligations",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Termination for Convenience.\n\n"
                        "(a) Either party may terminate this Agreement without cause at any time "
                        "upon [sixty (60)] days' prior written notice to the other party.\n\n"
                        "(b) If Client terminates under this Section, Client shall pay Service "
                        "Provider for all Services performed through the effective date of "
                        "termination, plus (i) any non-cancellable commitments made by Service "
                        "Provider in reliance on this Agreement; (ii) a wind-down fee equal to "
                        "[fifteen percent (15%)] of the fees for the remaining term; and (iii) "
                        "reasonable costs of transitioning the Services to Client or its designee.\n\n"
                        "(c) If Service Provider terminates under this Section, Service Provider "
                        "shall provide transition assistance for up to [ninety (90)] days at no "
                        "additional charge to Client.\n\n"
                        "(d) During the notice period, each party shall continue to perform its "
                        "obligations under this Agreement."
                    ),
                    "rationale": (
                        "Mutual termination for convenience with appropriate protections. The service "
                        "provider gets compensation for committed resources and wind-down. The client "
                        "gets transition assistance. This balances the flexibility of at-will "
                        "termination with commercial fairness."
                    ),
                    "confidence": 0.90,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Termination for convenience should be mutual",
                    "Service providers need compensation for committed resources and wind-down",
                    "Clients need transition assistance to ensure business continuity",
                    "Notice periods of 30-90 days are market standard",
                    "Performance obligations should continue during the notice period",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.TERMINATION_RIGHTS,
                title="No Cure Period for Payment Breach",
                scenario="SaaS agreement, vendor's form — immediate termination for late payment",
                original_clause=(
                    "Vendor may terminate this Agreement immediately upon written notice if "
                    "Client fails to pay any amount when due."
                ),
                bad_redline={
                    "proposed_text": (
                        "Vendor may terminate this Agreement upon 5 days written notice if Client "
                        "fails to pay any amount when due."
                    ),
                    "rationale": "5-day cure period is unreasonably short.",
                    "issues": [
                        "5 days is insufficient for legitimate payment processing delays",
                        "No distinction between disputed and undisputed amounts",
                        "No grace period for inadvertent late payments",
                        "Termination is disproportionate for a first late payment",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Termination for Non-Payment.\n\n"
                        "(a) If Client fails to pay any undisputed amount when due, Vendor shall "
                        "provide Client with written notice of such non-payment.\n\n"
                        "(b) Client shall have [fifteen (15)] days from receipt of such notice to "
                        "cure the non-payment.\n\n"
                        "(c) If Client disputes an amount in good faith, Client shall pay all "
                        "undisputed amounts when due. The disputed amount shall be resolved in "
                        "accordance with the dispute resolution provisions of this Agreement. "
                        "Vendor shall not terminate this Agreement for non-payment of a disputed "
                        "amount that is being resolved in good faith.\n\n"
                        "(d) If Client fails to cure the non-payment within the cure period, "
                        "Vendor may, in addition to any other remedies, suspend performance of "
                        "the Services until payment is received, and/or terminate this Agreement "
                        "upon written notice.\n\n"
                        "(e) For the avoidance of doubt, suspension of Services for non-payment "
                        "shall not constitute a breach by Vendor."
                    ),
                    "rationale": (
                        "Balanced payment termination provisions. The 15-day cure period is reasonable "
                        "for most payment delays. Disputed amounts are protected from termination. "
                        "Suspension of service is a proportional response before termination."
                    ),
                    "confidence": 0.94,
                    "attorney_review_required": False,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Payment breaches should have a reasonable cure period (10-30 days)",
                    "Disputed amounts should not trigger termination rights",
                    "Suspension of service is a more proportional remedy than termination",
                    "Require written notice before termination",
                    "Consider a graduated response: notice → suspension → termination",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.TERMINATION_RIGHTS,
                title="No Post-Termination Data Retrieval",
                scenario="Cloud services agreement, no mention of data export upon termination",
                original_clause=(
                    "Upon termination, Client's access to the Services shall be immediately "
                    "terminated. Vendor shall have no obligation to retain Client's data."
                ),
                bad_redline={
                    "proposed_text": (
                        "Upon termination, Vendor shall provide Client with access to export "
                        "its data for 30 days."
                    ),
                    "rationale": "Provides data access but no format specification or cost allocation.",
                    "issues": [
                        "No specification of export format",
                        "No obligation to provide data in a usable format",
                        "No obligation to assist with migration",
                        "30 days may be insufficient for large data volumes",
                        "No certification of data deletion",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Post-Termination Assistance.\n\n"
                        "(a) Data Export. Within [thirty (30)] days following the effective date "
                        "of termination, Vendor shall provide Client with a complete copy of Client's "
                        "data in a commercially reasonable, commonly used format (e.g., CSV, JSON, "
                        "or XML).\n\n"
                        "(b) Transition Assistance. Upon Client's request, Vendor shall provide "
                        "reasonable transition assistance for up to [ninety (90)] days following "
                        "termination, including technical support for data extraction and migration. "
                        "Transition assistance shall be provided at Vendor's then-current standard "
                        "rates.\n\n"
                        "(c) Data Deletion. Within [sixty (60)] days following the later of (i) the "
                        "effective date of termination or (ii) completion of data export under "
                        "Section (a), Vendor shall permanently delete or destroy all copies of "
                        "Client's data in its possession or control, except to the extent retention "
                        "is required by applicable law. Vendor shall provide Client with a written "
                        "certification of such deletion.\n\n"
                        "(d) Survival. This Section shall survive termination of this Agreement."
                    ),
                    "rationale": (
                        "Comprehensive post-termination data rights. Client gets their data in a "
                        "usable format with reasonable time to export. Transition assistance ensures "
                        "business continuity. The deletion certification provides audit trail. "
                        "Survival clause ensures these obligations persist."
                    ),
                    "confidence": 0.95,
                    "attorney_review_required": False,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Post-termination data retrieval is essential for cloud/SaaS agreements",
                    "Specify export format and timeline",
                    "Include transition assistance for business continuity",
                    "Data deletion certification provides compliance assurance",
                    "These obligations must survive termination",
                ],
            ),
        ]

    # ── Confidentiality Examples ─────────────────────────────────────────────

    def _confidentiality_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.CONFIDENTIALITY,
                title="Oral Information Not Covered",
                scenario="Joint venture NDA, excludes oral information from protection",
                original_clause=(
                    "Confidential Information means information that is (a) disclosed in writing "
                    "and marked 'Confidential' at the time of disclosure."
                ),
                bad_redline={
                    "proposed_text": (
                        "Confidential Information means information that is disclosed in writing "
                        "or orally."
                    ),
                    "rationale": "Includes oral info but no confirmation or reduction-to-writing requirement.",
                    "issues": [
                        "No requirement to confirm oral disclosures in writing within a reasonable time",
                        "Too broad — could cover casual conversations",
                        "No mechanism for designating oral information as confidential",
                        "Difficult to prove what was disclosed orally",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Definition of Confidential Information.\n\n"
                        "'Confidential Information' means any information, technical data, or "
                        "know-how, including but not limited to trade secrets, business plans, "
                        "customer data, financial information, and software, that is disclosed "
                        "by or on behalf of one party (the 'Disclosing Party') to the other "
                        "party (the 'Receiving Party'), in any form or medium, that:\n\n"
                        "(a) is disclosed in writing or in tangible form and is marked as "
                        "'Confidential' or with a similar legend at the time of disclosure; or\n\n"
                        "(b) is disclosed orally or visually, provided that such information is "
                        "(i) identified as confidential at the time of disclosure and (ii) reduced "
                        "to writing and marked as 'Confidential' within [thirty (30)] days of "
                        "disclosure.\n\n"
                        "Notwithstanding the foregoing, any information that the Receiving Party "
                        "knew or should have known, under the circumstances, was confidential or "
                        "proprietary shall be deemed Confidential Information regardless of marking."
                    ),
                    "rationale": (
                        "Comprehensive definition that covers all forms of disclosure. Oral "
                        "information is protected but requires timely written confirmation to "
                        "avoid disputes. The 'should have known' catch-all prevents a party from "
                        "avoiding protection by not marking documents."
                    ),
                    "confidence": 0.92,
                    "attorney_review_required": False,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Oral confidential information should be covered with a written confirmation requirement",
                    "Include a 'should have known' catch-all for unmarked information",
                    "Marking requirements should not be overly burdensome",
                    "30 days is standard for confirming oral disclosures in writing",
                    "Define the form and medium of disclosure comprehensively",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.CONFIDENTIALITY,
                title="No Standard of Care — Confidentiality Without Obligation",
                scenario="Vendor NDA — 'shall maintain confidentiality' but no standard specified",
                original_clause=(
                    "Receiving Party shall maintain the confidentiality of the Confidential Information."
                ),
                bad_redline={
                    "proposed_text": (
                        "Receiving Party shall use reasonable efforts to maintain the confidentiality "
                        "of the Confidential Information."
                    ),
                    "rationale": "'Reasonable efforts' is vague and may be insufficient.",
                    "issues": [
                        "'Reasonable efforts' is subjective and hard to enforce",
                        "No specific security measures required",
                        "No requirement to limit access to need-to-know personnel",
                        "No breach notification obligation",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Obligations of Confidentiality.\n\n"
                        "(a) The Receiving Party shall protect the Confidential Information using "
                        "the same degree of care that it uses to protect its own confidential "
                        "information of a similar nature, but in no event less than reasonable care.\n\n"
                        "(b) Without limiting the generality of Section (a), the Receiving Party "
                        "shall:\n"
                        "(i) restrict access to Confidential Information to those of its employees, "
                        "contractors, and advisors who have a legitimate need to know such information "
                        "for the purposes of this Agreement;\n"
                        "(ii) ensure that each such person is bound by confidentiality obligations "
                        "at least as protective as those set forth herein;\n"
                        "(iii) maintain appropriate physical, electronic, and procedural safeguards "
                        "to prevent unauthorized access, use, or disclosure;\n"
                        "(iv) not copy, reproduce, or reverse engineer Confidential Information "
                        "except as necessary to perform its obligations under this Agreement; and\n"
                        "(v) promptly notify the Disclosing Party upon becoming aware of any "
                        "unauthorized disclosure or use of Confidential Information.\n\n"
                        "(c) The Receiving Party shall be responsible for any breach of this Section "
                        "by any person to whom it provides access to Confidential Information."
                    ),
                    "rationale": (
                        "Clear, enforceable confidentiality obligations. The 'same degree of care' "
                        "standard is well-established in contract law and provides an objective "
                        "benchmark. Specific security measures and breach notification provide "
                        "accountability."
                    ),
                    "confidence": 0.93,
                    "attorney_review_required": False,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "'Same degree of care' is a stronger, more enforceable standard than 'reasonable efforts'",
                    "Specify minimum security measures",
                    "Require need-to-know access limitations",
                    "Include breach notification obligations",
                    "The receiving party should be responsible for its representatives' compliance",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.CONFIDENTIALITY,
                title="No Compelled Disclosure Notice",
                scenario="Government contractor NDA, requires disclosure under FOIA but no notice to disclosing party",
                original_clause=(
                    "Confidential Information may be disclosed as required by applicable law or "
                    "regulation."
                ),
                bad_redline={
                    "proposed_text": (
                        "Confidential Information may be disclosed as required by applicable law."
                    ),
                    "rationale": "Same provision, slightly reworded — still no notice requirement.",
                    "issues": [
                        "No obligation to notify the disclosing party before disclosure",
                        "No opportunity for the disclosing party to seek protective order",
                        "No limitation on the scope of compelled disclosure",
                        "No cooperation obligation",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Compelled Disclosure.\n\n"
                        "(a) If the Receiving Party is required by applicable law, regulation, or "
                        "valid legal process (including but not limited to a subpoena, court order, "
                        "or FOIA request) to disclose any Confidential Information, the Receiving "
                        "Party shall, to the extent permitted by law:\n"
                        "(i) promptly notify the Disclosing Party in writing of the requirement "
                        "before making any disclosure;\n"
                        "(ii) provide the Disclosing Party with a reasonable opportunity to seek "
                        "a protective order or other appropriate remedy; and\n"
                        "(iii) reasonably cooperate with the Disclosing Party's efforts to obtain "
                        "such protective order or remedy, at the Disclosing Party's expense.\n\n"
                        "(b) If a protective order is not obtained, the Receiving Party may disclose "
                        "only that portion of the Confidential Information that its legal counsel "
                        "advises is legally required, and shall exercise commercially reasonable "
                        "efforts to obtain confidential treatment for such disclosure.\n\n"
                        "(c) This Section does not alter the Receiving Party's obligation to comply "
                        "with applicable law."
                    ),
                    "rationale": (
                        "Properly drafted compelled disclosure provision. The disclosing party gets "
                        "timely notice and an opportunity to protect its information. The receiving "
                        "party is protected because they can comply with legal requirements. "
                        "Cooperation obligations are at the disclosing party's expense."
                    ),
                    "confidence": 0.94,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Always include a notice obligation for compelled disclosure",
                    "Give the disclosing party time to seek a protective order",
                    "Limit disclosure to what is legally required",
                    "Include a cooperation obligation (at disclosing party's expense)",
                    "This is especially important for government contractors and regulated industries",
                ],
            ),
        ]

    # ── Force Majeure Examples ───────────────────────────────────────────────

    def _force_majeure_examples(self) -> List[FewShotExample]:
        return [
            FewShotExample(
                clause_type=ClauseType.FORCE_MAJEURE,
                title="Pandemic Not Covered — Pre-2020 Language",
                scenario="Manufacturing supply agreement, force majeure clause from 2018",
                original_clause=(
                    "Neither party shall be liable for delays or failures in performance resulting "
                    "from acts of God, war, terrorism, or natural disasters."
                ),
                bad_redline={
                    "proposed_text": (
                        "Neither party shall be liable for delays or failures in performance "
                        "resulting from acts of God, war, terrorism, natural disasters, or "
                        "pandemics."
                    ),
                    "rationale": "Added pandemic but still too narrow and no mitigation obligation.",
                    "issues": [
                        "Still no coverage for government actions (closures, travel bans)",
                        "No coverage for supply chain disruptions",
                        "No coverage for cyberattacks",
                        "No mitigation obligation",
                        "No termination right for extended force majeure",
                        "No notice requirement",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Force Majeure.\n\n"
                        "(a) Definition. 'Force Majeure Event' means any event or circumstance "
                        "that is beyond the reasonable control of the affected party, including "
                        "but not limited to: acts of God; pandemics, epidemics, or public health "
                        "emergencies; war, terrorism, or civil unrest; government actions, orders, "
                        "or closures; natural disasters or severe weather; fire, explosion, or "
                        "accident; cyberattacks, ransomware, or other malicious cyber activities; "
                        "supply chain disruptions or material shortages; labor disputes or strikes; "
                        "and utility or telecommunications failures.\n\n"
                        "(b) Effect. If a party is prevented from performing its obligations due "
                        "to a Force Majeure Event, such performance shall be excused for the "
                        "duration of the Force Majeure Event, provided that the affected party:\n"
                        "(i) promptly notifies the other party in writing of the Force Majeure "
                        "Event, including its expected duration;\n"
                        "(ii) uses commercially reasonable efforts to mitigate the effects of the "
                        "Force Majeure Event and to resume performance as soon as practicable; and\n"
                        "(iii) continues to perform its obligations to the extent not prevented "
                        "by the Force Majeure Event.\n\n"
                        "(c) Exclusions. Force Majeure Events shall not excuse (i) payment "
                        "obligations; (ii) confidentiality obligations; or (iii) obligations "
                        "that could have been performed through alternative means.\n\n"
                        "(d) Termination. If a Force Majeure Event continues for more than [ninety "
                        "(90)] consecutive days, either party may terminate this Agreement upon "
                        "written notice without further liability, except for obligations accrued "
                        "prior to termination."
                    ),
                    "rationale": (
                        "Modern, comprehensive force majeure clause that addresses the full range "
                        "of risks in today's business environment. Includes pandemic, cyber, and "
                        "supply chain events. The mitigation obligation and notice requirement "
                        "are essential. Payment obligations are properly excluded."
                    ),
                    "confidence": 0.95,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Modern force majeure clauses must cover pandemics, cyberattacks, and supply chain disruptions",
                    "Include an affirmative mitigation obligation",
                    "Require prompt written notice of force majeure events",
                    "Payment obligations should never be excused by force majeure",
                    "Include a termination right for extended force majeure (90+ days)",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.FORCE_MAJEURE,
                title="Force Majeure as Blanket Excuse for All Obligations",
                scenario="Logistics services agreement, force majeure excuses everything including payment",
                original_clause=(
                    "In the event of a force majeure, all obligations of both parties shall be "
                    "suspended without liability."
                ),
                bad_redline={
                    "proposed_text": (
                        "In the event of a force majeure, the affected party's obligations shall "
                        "be suspended without liability."
                    ),
                    "rationale": "Still allows suspension of payment obligations.",
                    "issues": [
                        "Payment obligations should never be excused by force majeure",
                        "No obligation to continue unaffected obligations",
                        "No notice requirement",
                        "No mitigation obligation",
                        "No time limit on suspension",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Force Majeure.\n\n"
                        "(a) Subject to Section (b), if a party is prevented from performing its "
                        "obligations under this Agreement due to a Force Majeure Event (as defined "
                        "below), such party's performance shall be suspended for the duration of "
                        "the Force Majeure Event, and the affected party shall not be liable for "
                        "any resulting delay or failure.\n\n"
                        "(b) Force Majeure Events shall not excuse or suspend: (i) any payment "
                        "obligation of either party; (ii) any obligation of confidentiality; "
                        "(iii) any obligation to maintain insurance; or (iv) any obligation that "
                        "can be performed through alternative means or at an alternative location.\n\n"
                        "(c) The party claiming force majeure shall: (i) provide written notice "
                        "to the other party within [forty-eight (48)] hours of the onset of the "
                        "Force Majeure Event; (ii) provide periodic updates on the status and "
                        "expected duration; (iii) use diligent efforts to mitigate the impact and "
                        "resume performance; and (iv) continue to perform all obligations not "
                        "directly affected by the Force Majeure Event.\n\n"
                        "(d) 'Force Majeure Event' means any event beyond the reasonable control "
                        "of the affected party, including but not limited to: acts of God; "
                        "pandemics; war; terrorism; government actions; natural disasters; "
                        "cyberattacks; supply chain disruptions; labor disputes; and utility "
                        "failures."
                    ),
                    "rationale": (
                        "Properly scoped force majeure that protects both parties. Payment and "
                        "confidentiality obligations are never excused. The affected party has "
                        "clear notice, mitigation, and communication obligations. The definition "
                        "is comprehensive and modern."
                    ),
                    "confidence": 0.93,
                    "attorney_review_required": True,
                    "risk_impact": "high",
                },
                key_lessons=[
                    "Payment obligations must always be excluded from force majeure",
                    "Confidentiality and insurance obligations should also be excluded",
                    "The affected party should continue performing unaffected obligations",
                    "Require prompt notice and ongoing communication",
                    "Mitigation obligations prevent a party from simply 'waiting out' the event",
                ],
            ),
            FewShotExample(
                clause_type=ClauseType.FORCE_MAJEURE,
                title="No Termination Right for Extended Force Majeure",
                scenario="Long-term facilities management agreement, no exit for extended force majeure",
                original_clause=(
                    "Performance shall be excused for the duration of the force majeure event."
                ),
                bad_redline={
                    "proposed_text": (
                        "Performance shall be excused for the duration of the force majeure event, "
                        "and the affected party shall not be liable for any delays."
                    ),
                    "rationale": "Still no termination right — parties could be locked in indefinitely.",
                    "issues": [
                        "No termination right for either party",
                        "Parties could be trapped in a suspended contract indefinitely",
                        "No mechanism to wind down if force majeure is permanent",
                        "No allocation of risk for permanent impossibility",
                    ],
                },
                good_redline={
                    "proposed_text": (
                        "Force Majeure.\n\n"
                        "(a) If a party is delayed or prevented from performing its obligations "
                        "by a Force Majeure Event, such party shall promptly notify the other "
                        "party and shall be excused from performance to the extent of the "
                        "prevention, provided it uses reasonable efforts to mitigate.\n\n"
                        "(b) If a Force Majeure Event continues for more than [sixty (60)] "
                        "consecutive days, the parties shall meet to discuss a mutually acceptable "
                        "resolution, which may include modification of the affected obligations.\n\n"
                        "(c) If the parties are unable to reach a mutually acceptable resolution "
                        "within [thirty (30)] days of the meeting under Section (b), either party "
                        "may terminate this Agreement upon written notice. In the event of such "
                        "termination:\n"
                        "(i) Client shall pay Service Provider for all Services performed through "
                        "the date of termination;\n"
                        "(ii) Service Provider shall provide transition assistance for up to "
                        "[thirty (30)] days;\n"
                        "(iii) the parties shall return or destroy each other's confidential "
                        "information; and\n"
                        "(iv) Sections [survival clauses] shall survive termination.\n\n"
                        "(d) Termination under this Section shall be the sole and exclusive remedy "
                        "for Force Majeure Events continuing beyond the period specified in "
                        "Section (b)."
                    ),
                    "rationale": (
                        "Comprehensive force majeure with a clear path to termination. The 60-day "
                        "waiting period is reasonable. The mandatory meeting encourages resolution. "
                        "The termination provisions ensure an orderly wind-down. Making it the "
                        "exclusive remedy prevents disputes."
                    ),
                    "confidence": 0.91,
                    "attorney_review_required": True,
                    "risk_impact": "medium",
                },
                key_lessons=[
                    "Always include a termination right for extended force majeure",
                    "60-90 days is market standard before termination rights accrue",
                    "Include a mandatory meeting/negotiation step before termination",
                    "Provide for orderly wind-down: payment, transition, data return",
                    "Make the termination remedy exclusive to avoid disputes",
                ],
            ),
        ]
