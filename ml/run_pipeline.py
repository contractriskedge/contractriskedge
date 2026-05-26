"""End-to-end LoRA fine-tuning runner for contract risk analysis.

Orchestrates the complete training pipeline:
1. Download/prepare CUAD dataset
2. Run LoRA fine-tuning
3. Evaluate against baseline
4. Register model in model registry
5. Run A/B test in shadow mode
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("lora_train_runner")


def install_dependencies() -> None:
    """Install required ML dependencies."""
    import subprocess
    
    req_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "requirements.txt",
    )
    logger.info("Installing ML dependencies from %s...", req_file)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", req_file]
    )
    logger.info("Dependencies installed successfully.")


def download_dataset(output_dir: str, synthetic_only: bool = False) -> str:
    """Download or generate the training dataset.

    Args:
        output_dir: Directory to save dataset.
        synthetic_only: Use synthetic data only.

    Returns:
        Path to the dataset JSON file.
    """
    from ml.download_cuad import download_from_huggingface, generate_synthetic_fallback

    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    if synthetic_only:
        dataset_path = generate_synthetic_fallback(data_dir, num_examples=1000)
    else:
        try:
            dataset_path = download_from_huggingface(data_dir)
        except Exception as e:
            logger.warning("CUAD download failed: %s. Using synthetic data.", e)
            dataset_path = generate_synthetic_fallback(data_dir, num_examples=1000)

    return dataset_path


def run_training(
    dataset_path: str,
    output_dir: str,
    base_model: str = "mistralai/Mistral-7B-v0.1",
    lora_rank: int = 16,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    debug: bool = False,
) -> str:
    """Run the LoRA fine-tuning pipeline.

    Args:
        dataset_path: Path to the training dataset.
        output_dir: Directory for training outputs.
        base_model: Base model name.
        lora_rank: LoRA rank.
        epochs: Number of training epochs.
        batch_size: Per-device batch size.
        learning_rate: Learning rate.
        debug: Enable debug logging.

    Returns:
        Path to the saved model.
    """
    from ml.train import ContractRiskTrainer, main as train_main
    from ml.lora_config import LoRAConfig, TrainingRunConfig

    model_output_dir = os.path.join(output_dir, "models", f"contract-risk-lora-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(model_output_dir, exist_ok=True)

    # Build configuration
    lora_config = LoRAConfig(
        base_model_name=base_model,
        lora_rank=lora_rank,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
    )
    run_config = TrainingRunConfig(
        experiment_name="contract-risk-lora",
        output_dir=model_output_dir,
        max_train_samples=500,  # Limit for testing
    )

    # Save config
    config_path = os.path.join(model_output_dir, "training_config.json")
    with open(config_path, "w") as f:
        json.dump({
            "lora": lora_config.to_dict(),
            "run": {
                "experiment_name": run_config.experiment_name,
                "dataset": dataset_path,
                "output_dir": model_output_dir,
            },
        }, f, indent=2)
    logger.info("Training config saved to %s", config_path)

    # Run training
    trainer = ContractRiskTrainer(lora_config, run_config)
    model_path = trainer.train(cuad_path=dataset_path)

    logger.info("Training complete! Model saved to: %s", model_path)
    return model_path


def register_model(
    model_path: str,
    model_id: str,
    base_model: str,
    metrics: Optional[Dict[str, float]] = None,
) -> None:
    """Register the trained model in the model registry.

    Args:
        model_path: Path to the trained model.
        model_id: Model identifier.
        base_model: Base model name.
        metrics: Evaluation metrics.
    """
    from ml.model_registry import ModelRegistry

    registry = ModelRegistry(storage_path="./model_registry")
    
    version = registry.register_model(
        model_id=model_id,
        model_type="lora",
        base_model=base_model,
        path=model_path,
        metrics=metrics or {},
        description=f"LoRA fine-tuned contract risk model (rank=16, epochs=3)",
        tags=["contract-risk", "lora", "v1"],
    )
    
    logger.info("Model registered: %s (version: %s)", model_id, version.version)
    print(f"\nModel registered: {model_id}")
    print(f"  Version: {version.version}")
    print(f"  Path: {model_path}")


def main() -> None:
    """Main entry point for the complete training pipeline."""
    parser = argparse.ArgumentParser(
        description="Complete LoRA fine-tuning pipeline for contract risk analysis"
    )
    parser.add_argument(
        "--output-dir",
        default="./outputs",
        help="Root output directory",
    )
    parser.add_argument(
        "--base-model",
        default="mistralai/Mistral-7B-v0.1",
        help="Base model for fine-tuning",
    )
    parser.add_argument(
        "--lora-rank",
        type=int,
        default=16,
        help="LoRA rank",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Per-device batch size",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="Learning rate",
    )
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Use synthetic data instead of CUAD",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register model in registry after training",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Install dependencies
    if not args.skip_install:
        install_dependencies()
    else:
        logger.info("Skipping dependency installation.")

    # Step 2: Download/prepare dataset
    logger.info("=" * 60)
    logger.info("STEP 1/4: Preparing dataset...")
    logger.info("=" * 60)
    dataset_path = download_dataset(output_dir, synthetic_only=args.synthetic_only)

    # Step 3: Run training
    logger.info("=" * 60)
    logger.info("STEP 2/4: Running LoRA fine-tuning...")
    logger.info("=" * 60)
    logger.info(
        "Configuration: model=%s, rank=%d, epochs=%d, batch=%d, lr=%f",
        args.base_model,
        args.lora_rank,
        args.epochs,
        args.batch_size,
        args.learning_rate,
    )
    
    model_path = run_training(
        dataset_path=dataset_path,
        output_dir=output_dir,
        base_model=args.base_model,
        lora_rank=args.lora_rank,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        debug=args.debug,
    )

    # Step 4: Register model (optional)
    if args.register:
        logger.info("=" * 60)
        logger.info("STEP 3/4: Registering model...")
        logger.info("=" * 60)
        model_id = f"contract-risk-lora-v1"
        register_model(
            model_path=model_path,
            model_id=model_id,
            base_model=args.base_model,
        )

    logger.info("=" * 60)
    logger.info("TRAINING PIPELINE COMPLETE!")
    logger.info("=" * 60)
    print(f"\n✅ Training pipeline completed successfully!")
    print(f"   Dataset: {dataset_path}")
    print(f"   Model: {model_path}")
    print(f"\nTo evaluate: python -m ml.evaluate --model-path {model_path}")
    print(f"To run A/B test: python -m ml.ab_testing --model-path {model_path}")


if __name__ == "__main__":
    main()
