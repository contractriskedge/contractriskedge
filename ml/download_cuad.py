"""Download the CUAD dataset for contract risk fine-tuning.

Downloads the Contract Understanding Atticus Dataset (CUAD) from HuggingFace
and prepares it for the LoRA fine-tuning pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("download_cuad")


def download_from_huggingface(output_path: str) -> str:
    """Download CUAD dataset from HuggingFace Datasets.

    Args:
        output_path: Directory to save the dataset.

    Returns:
        Path to the saved JSON file.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error(
            "datasets package not installed. Install with: pip install datasets"
        )
        sys.exit(1)

    logger.info("Downloading CUAD dataset from HuggingFace...")
    
    # Load the CUAD dataset
    dataset = load_dataset("cuad", trust_remote_code=True)
    
    output_file = os.path.join(output_path, "cuad.json")
    os.makedirs(output_path, exist_ok=True)
    
    # Convert to our expected format
    cuad_data = []
    
    for split in ["train", "test", "validation"]:
        if split not in dataset:
            continue
        for example in dataset[split]:
            cuad_data.append({
                "title": example.get("title", ""),
                "clauses": [{
                    "text": example.get("clause", ""),
                    "question": example.get("question", ""),
                    "answer": example.get("answer", "Yes"),
                    "label": example.get("label", ""),
                }],
            })
    
    with open(output_file, "w") as f:
        json.dump({"data": cuad_data}, f, indent=2)
    
    logger.info(
        "CUAD dataset saved to %s (%d documents)",
        output_file,
        len(cuad_data),
    )
    return output_file


def generate_synthetic_fallback(output_path: str, num_examples: int = 1000) -> str:
    """Generate synthetic training data as fallback if CUAD is unavailable.

    Creates realistic contract clause examples with risk labels for testing
    the training pipeline end-to-end.

    Args:
        output_path: Directory to save the dataset.
        num_examples: Number of synthetic examples to generate.

    Returns:
        Path to the saved JSON file.
    """
    import random

    random.seed(42)
    
    clause_templates = [
        {
            "text": "Neither party shall be liable for any indirect, incidental, special, consequential or punitive damages. The total liability of either party shall not exceed ${amount}.",
            "category": "liability_limitation",
            "severity": 7,
        },
        {
            "text": "The Vendor agrees to indemnify, defend, and hold harmless the Client from and against any and all claims, losses, liabilities, and expenses arising out of or related to this Agreement.",
            "category": "indemnification",
            "severity": 5,
        },
        {
            "text": "All intellectual property rights in any deliverables created under this Agreement shall be the sole and exclusive property of the Client.",
            "category": "intellectual_property",
            "severity": 3,
        },
        {
            "text": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles.",
            "category": "governing_law",
            "severity": 4,
        },
        {
            "text": "Either party may terminate this Agreement upon {days} days' prior written notice to the other party.",
            "category": "termination",
            "severity": 3,
        },
        {
            "text": "The Receiving Party shall maintain the Confidential Information in strict confidence and shall not disclose it to any third party for a period of {years} years.",
            "category": "confidentiality",
            "severity": 4,
        },
        {
            "text": "Neither party shall be liable for any failure or delay in performance due to causes beyond its reasonable control, including but not limited to acts of God, war, terrorism, pandemics, and government actions.",
            "category": "force_majeure",
            "severity": 2,
        },
        {
            "text": "All fees are due within {days} days of invoice date. Late payments shall accrue interest at {rate}% per month.",
            "category": "payment_terms",
            "severity": 5,
        },
    ]

    output_file = os.path.join(output_path, "cuad_synthetic.json")
    os.makedirs(output_path, exist_ok=True)
    
    documents = []
    for i in range(num_examples):
        template = random.choice(clause_templates)
        clause_text = template["text"].format(
            amount=random.choice(["50,000", "100,000", "500,000", "1,000,000", "5,000,000"]),
            days=random.choice([30, 60, 90, 180]),
            years=random.choice([1, 2, 3, 5]),
            rate=random.choice(["1.0", "1.5", "2.0"]),
        )
        
        documents.append({
            "title": f"Synthetic Contract {i+1}",
            "clauses": [{
                "text": clause_text,
                "question": template["category"],
                "answer": "Yes",
                "label": template["category"],
            }],
        })
    
    with open(output_file, "w") as f:
        json.dump({"data": documents}, f, indent=2)
    
    logger.info(
        "Synthetic dataset saved to %s (%d examples)",
        output_file,
        len(documents),
    )
    return output_file


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download CUAD dataset for contract risk fine-tuning"
    )
    parser.add_argument(
        "--output-dir",
        default="./data",
        help="Directory to save the dataset",
    )
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Generate synthetic data only (skip HuggingFace download)",
    )
    parser.add_argument(
        "--num-synthetic",
        type=int,
        default=1000,
        help="Number of synthetic examples to generate",
    )
    
    args = parser.parse_args()
    
    output_path = os.path.abspath(args.output_dir)
    
    if args.synthetic_only:
        generate_synthetic_fallback(output_path, args.num_synthetic)
    else:
        try:
            download_from_huggingface(output_path)
        except Exception as e:
            logger.warning(
                "Failed to download CUAD: %s. Generating synthetic fallback.",
                e,
            )
            generate_synthetic_fallback(output_path, args.num_synthetic)
    
    logger.info("Dataset preparation complete!")
    print(f"\nDataset saved to: {output_path}")
    print(f"Run training with: python -m ml.train --cuad-path {output_path}/cuad.json")


if __name__ == "__main__":
    main()
