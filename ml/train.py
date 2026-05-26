"""Complete LoRA fine-tuning training script using HuggingFace PEFT + Accelerate.

Provides a production-ready training script for fine-tuning language
models on contract risk analysis using LoRA with PEFT and Accelerate.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .lora_config import LoRAConfig, TrainingRunConfig
from .dataset import CUDADatasetProcessor, InstructionExample

logger = logging.getLogger(__name__)


class ContractRiskTrainer:
    """LoRA fine-tuning trainer for contract risk analysis models.

    Provides a complete training pipeline using HuggingFace PEFT,
    Transformers, and Accelerate for efficient fine-tuning.

    Usage:
        config = LoRAConfig()
        run_config = TrainingRunConfig()
        trainer = ContractRiskTrainer(config, run_config)
        trainer.train()
    """

    def __init__(
        self,
        lora_config: LoRAConfig,
        run_config: TrainingRunConfig,
    ) -> None:
        """Initialize the trainer.

        Args:
            lora_config: LoRA hyperparameters.
            run_config: Training run configuration.
        """
        self._lora_config = lora_config
        self._run_config = run_config
        self._model = None
        self._tokenizer = None
        self._trainer = None

    def setup(self) -> None:
        """Set up model, tokenizer, and training components."""
        self._setup_model_and_tokenizer()
        self._setup_peft()
        self._setup_training_args()

    def _setup_model_and_tokenizer(self) -> None:
        """Load base model and tokenizer with quantization."""
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        logger.info(
            "Loading base model: %s", self._lora_config.base_model_name
        )

        # Quantization config
        bnb_config = None
        if self._lora_config.load_in_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type=self._lora_config.bnb_4bit_quant_type,
                bnb_4bit_use_double_quant=self._lora_config.bnb_4bit_use_double_quant,
            )

        # Load model
        self._model = AutoModelForCausalLM.from_pretrained(
            self._lora_config.base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            attn_implementation=self._lora_config.attn_implementation,
        )

        # Enable gradient checkpointing
        if self._lora_config.gradient_checkpointing:
            self._model.gradient_checkpointing_enable()

        # Load tokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(
            self._lora_config.base_model_name,
            trust_remote_code=True,
        )

        # Set padding token
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        logger.info("Model and tokenizer loaded successfully")

    def _setup_peft(self) -> None:
        """Configure LoRA adapters using PEFT."""
        from peft import LoraConfig, get_peft_model, TaskType

        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self._lora_config.lora_rank,
            lora_alpha=self._lora_config.lora_alpha,
            lora_dropout=self._lora_config.lora_dropout,
            bias=self._lora_config.lora_bias,
            target_modules=self._lora_config.target_modules,
            modules_to_save=self._lora_config.modules_to_save,
            use_rslora=self._lora_config.use_rslora,
            use_dora=self._lora_config.use_dora,
            init_lora_weights=self._lora_config.lora_init_method,
        )

        self._model = get_peft_model(self._model, peft_config)
        self._model.print_trainable_parameters()

        logger.info(
            "LoRA adapters configured: rank=%d, alpha=%d, dropout=%.2f",
            self._lora_config.lora_rank,
            self._lora_config.lora_alpha,
            self._lora_config.lora_dropout,
        )

    def _setup_training_args(self) -> None:
        """Configure training arguments."""
        from transformers import TrainingArguments

        run_name = (
            self._run_config.run_name
            or f"{self._run_config.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        training_args = TrainingArguments(
            output_dir=self._run_config.output_dir,
            run_name=run_name,
            learning_rate=self._lora_config.learning_rate,
            lr_scheduler_type=self._lora_config.lr_scheduler_type,
            warmup_ratio=self._lora_config.warmup_ratio,
            num_train_epochs=self._lora_config.num_train_epochs,
            per_device_train_batch_size=self._lora_config.per_device_train_batch_size,
            per_device_eval_batch_size=self._lora_config.per_device_eval_batch_size,
            gradient_accumulation_steps=self._lora_config.gradient_accumulation_steps,
            gradient_checkpointing=self._lora_config.gradient_checkpointing,
            optim=self._lora_config.optim,
            max_grad_norm=self._lora_config.max_grad_norm,
            weight_decay=self._lora_config.weight_decay,
            eval_strategy=self._lora_config.eval_strategy,
            eval_steps=self._lora_config.eval_steps,
            save_strategy=self._lora_config.save_strategy,
            save_steps=self._lora_config.save_steps,
            save_total_limit=self._lora_config.save_total_limit,
            load_best_model_at_end=self._lora_config.load_best_model_at_end,
            metric_for_best_model=self._lora_config.metric_for_best_model,
            greater_is_better=self._lora_config.greater_is_better,
            logging_strategy=self._lora_config.logging_strategy,
            logging_steps=self._lora_config.logging_steps,
            report_to=self._lora_config.report_to,
            fp16=False,
            bf16=True,
            ddp_find_unused_parameters=False,
            remove_unused_columns=True,
            dataloader_num_workers=4,
            group_by_length=True,
            seed=self._run_config.seed,
            data_seed=self._run_config.data_seed,
        )

        self._training_args = training_args
        logger.info("Training arguments configured")

    def _tokenize_function(self, examples: Dict[str, List]) -> Dict[str, Any]:
        """Tokenize a batch of examples.

        Args:
            examples: Batch of text examples.

        Returns:
            Tokenized inputs with labels.
        """
        tokenized = self._tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=self._lora_config.max_seq_length,
            return_tensors=None,
        )

        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    def prepare_dataset(
        self,
        cuad_path: Optional[str] = None,
    ) -> Tuple[Any, Any, Any]:
        """Prepare train/validation/test datasets.

        Args:
            cuad_path: Optional path to CUAD dataset.

        Returns:
            Tuple of (train_dataset, eval_dataset, test_dataset).
        """
        from datasets import Dataset

        processor = CUDADatasetProcessor()

        # Load and process CUAD
        all_examples = processor.load_and_process(
            cuad_path or "./data/cuad.json",
            max_examples=self._run_config.max_train_samples,
        )

        # Split
        train_examples, val_examples, test_examples = processor.train_test_split(
            all_examples,
            test_ratio=0.1,
            val_ratio=0.1,
        )

        # Format for training
        train_texts = processor.format_for_training(train_examples, "llama")
        val_texts = processor.format_for_training(val_examples, "llama")
        test_texts = processor.format_for_training(test_examples, "llama")

        # Create HuggingFace datasets
        train_dataset = Dataset.from_dict({"text": train_texts})
        eval_dataset = Dataset.from_dict({"text": val_texts})
        test_dataset = Dataset.from_dict({"text": test_texts})

        # Tokenize
        train_dataset = train_dataset.map(
            self._tokenize_function,
            batched=True,
            remove_columns=["text"],
            num_proc=self._lora_config.preprocessing_num_workers,
        )
        eval_dataset = eval_dataset.map(
            self._tokenize_function,
            batched=True,
            remove_columns=["text"],
            num_proc=self._lora_config.preprocessing_num_workers,
        )
        test_dataset = test_dataset.map(
            self._tokenize_function,
            batched=True,
            remove_columns=["text"],
            num_proc=self._lora_config.preprocessing_num_workers,
        )

        logger.info(
            "Datasets prepared: %d train, %d eval, %d test",
            len(train_dataset),
            len(eval_dataset),
            len(test_dataset),
        )

        return train_dataset, eval_dataset, test_dataset

    def _compute_metrics(self, eval_preds: Any) -> Dict[str, float]:
        """Compute evaluation metrics.

        Args:
            eval_preds: Evaluation predictions from the trainer.

        Returns:
            Dict of metric names to values.
        """
        predictions, labels = eval_preds

        # Decode predictions and labels
        predictions = np.argmax(predictions, axis=-1)

        # Compute perplexity
        import torch
        from torch.nn import CrossEntropyLoss

        loss_fct = CrossEntropyLoss()
        shift_logits = torch.tensor(predictions[..., :-1, :])
        shift_labels = torch.tensor(labels[..., 1:])
        loss = loss_fct(
            shift_logits.reshape(-1, shift_logits.size(-1)),
            shift_labels.reshape(-1),
        )
        perplexity = torch.exp(loss).item()

        return {"perplexity": perplexity}

    def train(self, cuad_path: Optional[str] = None) -> str:
        """Run the full training pipeline.

        Args:
            cuad_path: Optional path to CUAD dataset.

        Returns:
            Path to the saved model.
        """
        from transformers import Trainer

        self.setup()

        # Prepare datasets
        train_dataset, eval_dataset, _ = self.prepare_dataset(cuad_path)

        # Create trainer
        self._trainer = Trainer(
            model=self._model,
            args=self._training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self._tokenizer,
            compute_metrics=self._compute_metrics,
        )

        # Train
        logger.info("Starting training...")
        train_result = self._trainer.train()

        # Save
        self._trainer.save_model()
        self._tokenizer.save_pretrained(self._run_config.output_dir)

        # Save training metrics
        metrics = train_result.metrics
        metrics["train_samples"] = len(train_dataset)
        with open(
            os.path.join(self._run_config.output_dir, "train_metrics.json"), "w"
        ) as f:
            json.dump(metrics, f, indent=2, default=str)

        logger.info(
            "Training completed. Model saved to %s",
            self._run_config.output_dir,
        )

        return self._run_config.output_dir

    def evaluate(self, test_dataset: Optional[Any] = None) -> Dict[str, float]:
        """Evaluate the trained model.

        Args:
            test_dataset: Optional test dataset. If None, loads from config.

        Returns:
            Dict of evaluation metrics.
        """
        if self._trainer is None:
            raise RuntimeError("Trainer not initialized. Call train() first.")

        if test_dataset is None:
            _, _, test_dataset = self.prepare_dataset()

        metrics = self._trainer.evaluate(test_dataset)
        logger.info("Evaluation metrics: %s", metrics)
        return metrics

    def save_for_inference(self, output_path: str) -> None:
        """Save the model in inference-optimized format.

        Args:
            output_path: Directory to save the merged model.
        """
        import torch
        from peft import PeftModel

        if self._model is None:
            raise RuntimeError("No model to save. Train or load first.")

        # Merge LoRA weights and save
        merged_model = self._model.merge_and_unload()
        merged_model.save_pretrained(output_path)
        self._tokenizer.save_pretrained(output_path)

        logger.info("Inference model saved to %s", output_path)


def main() -> None:
    """Entry point for command-line training."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fine-tune a contract risk analysis model with LoRA"
    )
    parser.add_argument(
        "--config", type=str, help="Path to JSON configuration file"
    )
    parser.add_argument(
        "--cuad-path", type=str, help="Path to CUAD dataset"
    )
    parser.add_argument(
        "--output-dir", type=str, default="./outputs",
        help="Output directory for model"
    )
    parser.add_argument(
        "--base-model", type=str,
        default="mistralai/Mistral-7B-v0.1",
        help="Base model name",
    )
    parser.add_argument(
        "--lora-rank", type=int, default=16,
        help="LoRA rank",
    )
    parser.add_argument(
        "--epochs", type=int, default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size", type=int, default=4,
        help="Per-device batch size",
    )
    parser.add_argument(
        "--learning-rate", type=float, default=2e-4,
        help="Learning rate",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Build config
    if args.config:
        with open(args.config) as f:
            config_data = json.load(f)
        lora_config = LoRAConfig.from_dict(config_data.get("lora", {}))
        run_config = TrainingRunConfig(**config_data.get("run", {}))
    else:
        lora_config = LoRAConfig(
            base_model_name=args.base_model,
            lora_rank=args.lora_rank,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            learning_rate=args.learning_rate,
        )
        run_config = TrainingRunConfig(
            output_dir=args.output_dir,
        )

    # Run training
    trainer = ContractRiskTrainer(lora_config, run_config)
    model_path = trainer.train(args.cuad_path)

    print(f"\nTraining complete! Model saved to: {model_path}")


if __name__ == "__main__":
    main()
