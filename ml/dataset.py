"""CUAD dataset processor for instruction-tuning format.

Processes the Contract Understanding Atticus Dataset (CUAD) into
instruction-tuning format for fine-tuning language models on
contract risk analysis tasks.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class InstructionExample:
    """A single instruction-tuning example."""

    instruction: str
    input_text: str
    output_text: str
    category: Optional[str] = None
    severity: Optional[int] = None
    source: str = "cuad"


class CUDADatasetProcessor:
    """Processes the CUAD dataset into instruction-tuning format.

    Transforms the Contract Understanding Atticus Dataset into
    structured instruction-tuning examples for risk analysis
    fine-tuning.

    Usage:
        processor = CUDADatasetProcessor()
        examples = processor.load_and_process("path/to/cuad.json")
        train, eval = processor.train_test_split(examples)
    """

    # Instruction templates for different task types
    CLASSIFICATION_INSTRUCTION = (
        "Classify the following contract clause into the appropriate "
        "risk category and identify the specific risk sub-type."
    )

    SEVERITY_INSTRUCTION = (
        "Assess the severity of risk in the following contract clause "
        "on a scale of 1-10, where 1 is minimal risk and 10 is critical risk."
    )

    ANALYSIS_INSTRUCTION = (
        "Analyze the following contract clause for potential risks. "
        "Identify the risk category, assess severity, and provide "
        "a detailed rationale for your assessment."
    )

    # CUAD question types mapped to risk categories
    CUAD_TO_RISK_CATEGORY: Dict[str, str] = {
        "Indemnification": "indemnification",
        "Limitation_of_Liability": "liability_limitation",
        "Termination_for_Convenience": "termination",
        "Termination_for_Cause": "termination",
        "Confidentiality": "confidentiality",
        "Data_Privacy": "data_privacy",
        "Anti-Corruption": "compliance",
        "Non-Compete": "non_compete",
        "Non-Solicit": "non_compete",
        "IP_Ownership": "intellectual_property",
        "License_Grant": "intellectual_property",
        "Payment_Terms": "payment_terms",
        "Force_Majeure": "force_majeure",
        "Assignment": "assignment",
        "Governing_Law": "governing_law",
        "Revenue_Sharing": "payment_terms",
        "Joint_IP": "intellectual_property",
    }

    def __init__(
        self,
        max_length: int = 2048,
        include_negatives: bool = False,
        seed: int = 42,
    ) -> None:
        """Initialize the dataset processor.

        Args:
            max_length: Maximum sequence length for tokenization.
            include_negatives: Whether to include negative examples.
            seed: Random seed for reproducibility.
        """
        self._max_length = max_length
        self._include_negatives = include_negatives
        self._random = random.Random(seed)

    def load_and_process(
        self,
        cuad_path: str,
        max_examples: Optional[int] = None,
    ) -> List[InstructionExample]:
        """Load CUAD dataset and process into instruction examples.

        Args:
            cuad_path: Path to CUAD JSON file.
            max_examples: Maximum number of examples to process.

        Returns:
            List of instruction-tuning examples.
        """
        logger.info("Loading CUAD dataset from %s", cuad_path)

        try:
            with open(cuad_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.warning(
                "CUAD dataset not found at %s. Generating synthetic examples.",
                cuad_path,
            )
            return self._generate_synthetic_examples(max_examples or 500)

        examples: list[InstructionExample] = []
        documents = data if isinstance(data, list) else data.get("data", [])

        for doc in documents:
            doc_examples = self._process_document(doc)
            examples.extend(doc_examples)

            if max_examples and len(examples) >= max_examples:
                examples = examples[:max_examples]
                break

        logger.info(
            "Processed %d instruction examples from CUAD", len(examples)
        )
        return examples

    def _process_document(
        self, document: Dict[str, Any]
    ) -> List[InstructionExample]:
        """Process a single CUAD document.

        Args:
            document: CUAD document dict.

        Returns:
            List of instruction examples from this document.
        """
        examples: list[InstructionExample] = []
        clauses = document.get("clauses", document.get("annotations", []))

        for clause in clauses:
            clause_text = clause.get("text", clause.get("clause", ""))
            if not clause_text or len(clause_text) < 20:
                continue

            question = clause.get("question", "")
            answer = clause.get("answer", clause.get("label", ""))

            # Map CUAD question to risk category
            category = self._map_question_to_category(question)

            if category:
                examples.append(
                    InstructionExample(
                        instruction=self.CLASSIFICATION_INSTRUCTION,
                        input_text=clause_text,
                        output_text=json.dumps({
                            "category": category,
                            "clause_type": question,
                            "is_relevant": answer == "Yes",
                        }),
                        category=category,
                        source="cuad",
                    )
                )

        return examples

    def _map_question_to_category(self, question: str) -> Optional[str]:
        """Map a CUAD question type to a risk category.

        Args:
            question: CUAD question type string.

        Returns:
            Risk category ID or None if unmappable.
        """
        # Direct match
        if question in self.CUAD_TO_RISK_CATEGORY:
            return self.CUAD_TO_RISK_CATEGORY[question]

        # Partial match
        for cuad_type, category in self.CUAD_TO_RISK_CATEGORY.items():
            if cuad_type.lower() in question.lower():
                return category

        return None

    def _generate_synthetic_examples(
        self, count: int
    ) -> List[InstructionExample]:
        """Generate synthetic training examples when CUAD is unavailable.

        Creates realistic instruction-tuning examples based on common
        contract clause patterns for each risk category.

        Args:
            count: Number of examples to generate.

        Returns:
            List of synthetic instruction examples.
        """
        synthetic_categories = [
            ("indemnification", "Indemnification", [
                "The Company shall indemnify and hold harmless the Client from any and all claims.",
                "Provider agrees to indemnify Customer against all third-party claims arising from the Services.",
                "Each party shall indemnify the other for losses resulting from its negligence.",
            ]),
            ("liability_limitation", "Limitation of Liability", [
                "Neither party's aggregate liability shall exceed the fees paid under this Agreement.",
                "In no event shall either party be liable for any indirect or consequential damages.",
                "Total liability cap is set at $1,000,000 per occurrence.",
            ]),
            ("termination", "Termination", [
                "Either party may terminate this Agreement upon 30 days written notice.",
                "This Agreement may be terminated for cause if a material breach is not cured within 60 days.",
                "Provider may terminate immediately if Customer fails to pay within 15 days.",
            ]),
            ("confidentiality", "Confidentiality", [
                "Receiving party shall protect Confidential Information using reasonable care.",
                "Confidential Information includes all business and technical information disclosed.",
                "Confidentiality obligations survive termination for a period of 3 years.",
            ]),
            ("data_privacy", "Data Privacy", [
                "Provider shall implement appropriate technical and organizational security measures.",
                "Personal data shall only be processed in accordance with the Data Processing Agreement.",
                "Both parties shall comply with applicable data protection laws including GDPR.",
            ]),
            ("compliance", "Regulatory Compliance", [
                "Each party shall comply with all applicable laws and regulations.",
                "Provider represents compliance with the Foreign Corrupt Practices Act.",
                "Services shall comply with all industry-specific regulatory requirements.",
            ]),
            ("payment_terms", "Payment Terms", [
                "All invoices are due within 30 days of receipt.",
                "Late payments shall accrue interest at 1.5% per month.",
                "Prices are subject to annual adjustment based on CPI.",
            ]),
            ("force_majeure", "Force Majeure", [
                "Neither party shall be liable for delays caused by force majeure events.",
                "Force majeure includes acts of God, war, terrorism, and pandemics.",
                "If force majeure continues for 90 days, either party may terminate.",
            ]),
            ("assignment", "Assignment", [
                "Neither party may assign this Agreement without the other's written consent.",
                "Assignment to affiliates is permitted without consent.",
                "Change of control shall not be deemed an assignment.",
            ]),
            ("governing_law", "Governing Law", [
                "This Agreement shall be governed by the laws of the State of New York.",
                "Any disputes shall be resolved in the courts of Delaware.",
                "The parties submit to the exclusive jurisdiction of the federal courts.",
            ]),
            ("non_compete", "Non-Compete", [
                "Provider shall not engage in any competing business for 12 months.",
                "During the term and for one year after, neither party shall solicit the other's employees.",
                "Non-compete is limited to the specific services provided under this Agreement.",
            ]),
            ("intellectual_property", "Intellectual Property", [
                "All work product shall be owned exclusively by Customer.",
                "Provider retains all rights in its pre-existing intellectual property.",
                "Customer receives a perpetual, irrevocable license to use the deliverables.",
            ]),
        ]

        examples: list[InstructionExample] = []
        examples_per_category = count // len(synthetic_categories)

        for cat_id, cat_name, clause_templates in synthetic_categories:
            for i in range(examples_per_category):
                clause = self._random.choice(clause_templates)
                severity = self._random.randint(3, 8)

                examples.append(
                    InstructionExample(
                        instruction=self.ANALYSIS_INSTRUCTION,
                        input_text=clause,
                        output_text=json.dumps({
                            "category": cat_id,
                            "category_name": cat_name,
                            "severity_score": severity,
                            "confidence": "medium",
                            "rationale": (
                                f"This {cat_name.lower()} clause presents "
                                f"{'significant' if severity > 5 else 'moderate'} risk. "
                                f"The language is {'aggressive' if severity > 6 else 'standard'} "
                                f"compared to market benchmarks."
                            ),
                        }),
                        category=cat_id,
                        severity=severity,
                        source="synthetic",
                    )
                )

        self._random.shuffle(examples)
        logger.info(
            "Generated %d synthetic training examples across %d categories",
            len(examples),
            len(synthetic_categories),
        )
        return examples

    def train_test_split(
        self,
        examples: List[InstructionExample],
        test_ratio: float = 0.1,
        val_ratio: float = 0.1,
    ) -> Tuple[List[InstructionExample], List[InstructionExample], List[InstructionExample]]:
        """Split examples into train/validation/test sets.

        Performs stratified split by category to maintain distribution.

        Args:
            examples: Full list of examples.
            test_ratio: Proportion for test set.
            val_ratio: Proportion for validation set.

        Returns:
            Tuple of (train, validation, test) examples.
        """
        # Group by category
        by_category: Dict[str, list[InstructionExample]] = {}
        for ex in examples:
            cat = ex.category or "unknown"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(ex)

        train: list[InstructionExample] = []
        val: list[InstructionExample] = []
        test: list[InstructionExample] = []

        for cat, cat_examples in by_category.items():
            self._random.shuffle(cat_examples)
            n = len(cat_examples)
            n_test = max(1, int(n * test_ratio))
            n_val = max(1, int(n * val_ratio))
            n_train = n - n_test - n_val

            train.extend(cat_examples[:n_train])
            val.extend(cat_examples[n_train:n_train + n_val])
            test.extend(cat_examples[n_train + n_val:])

        self._random.shuffle(train)
        self._random.shuffle(val)
        self._random.shuffle(test)

        logger.info(
            "Split: %d train, %d validation, %d test",
            len(train), len(val), len(test),
        )
        return train, val, test

    def format_for_training(
        self,
        examples: List[InstructionExample],
        template: str = "llama",
    ) -> List[str]:
        """Format examples for training with a specific template.

        Args:
            examples: Instruction examples.
            template: Template format ('llama', 'mistral', 'chatml').

        Returns:
            List of formatted text strings.
        """
        if template == "llama":
            return [
                f"<s>[INST] {ex.instruction}\n\n{ex.input_text} [/INST] "
                f"{ex.output_text}</s>"
                for ex in examples
            ]
        elif template == "mistral":
            return [
                f"<s>[INST] {ex.instruction}\n\n{ex.input_text} [/INST]"
                f"{ex.output_text}</s>"
                for ex in examples
            ]
        elif template == "chatml":
            return [
                f"<|im_start|>system\n{ex.instruction}<|im_end|>\n"
                f"<|im_start|>user\n{ex.input_text}<|im_end|>\n"
                f"<|im_start|>assistant\n{ex.output_text}<|im_end|>"
                for ex in examples
            ]
        else:
            raise ValueError(f"Unknown template: {template}")

    def get_category_distribution(
        self, examples: List[InstructionExample]
    ) -> Dict[str, int]:
        """Get the distribution of categories in a dataset.

        Args:
            examples: List of instruction examples.

        Returns:
            Dict mapping category to count.
        """
        dist: Dict[str, int] = {}
        for ex in examples:
            cat = ex.category or "unknown"
            dist[cat] = dist.get(cat, 0) + 1
        return dict(sorted(dist.items()))
