"""LoRA hyperparameters and configuration for contract model fine-tuning.

Defines LoRA (Low-Rank Adaptation) configuration for fine-tuning
language models on contract risk analysis tasks. Includes rank,
alpha, target modules, dropout, and optimizer settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LoRAConfig:
    """Configuration for LoRA fine-tuning.

    Defines all hyperparameters needed for LoRA-based fine-tuning
    of language models for contract risk analysis.

    Usage:
        config = LoRAConfig(
            base_model_name="mistralai/Mistral-7B-v0.1",
            lora_rank=16,
            lora_alpha=32,
        )
    """

    # Model configuration
    base_model_name: str = "mistralai/Mistral-7B-v0.1"
    model_max_length: int = 4096
    torch_dtype: str = "bfloat16"
    attn_implementation: str = "flash_attention_2"
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True

    # LoRA hyperparameters
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_bias: str = "none"
    lora_task_type: str = "CAUSAL_LM"

    # Target modules for LoRA (Mistral/Llama architecture)
    target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )
    modules_to_save: Optional[List[str]] = None

    # Training hyperparameters
    learning_rate: float = 2e-4
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.03
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    gradient_checkpointing: bool = True
    optim: str = "paged_adamw_8bit"
    max_grad_norm: float = 0.3
    weight_decay: float = 0.001

    # Evaluation and saving
    eval_strategy: str = "steps"
    eval_steps: int = 100
    save_strategy: str = "steps"
    save_steps: int = 100
    save_total_limit: int = 3
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False

    # Logging
    logging_strategy: str = "steps"
    logging_steps: int = 10
    report_to: List[str] = field(
        default_factory=lambda: ["tensorboard"]
    )
    run_name: Optional[str] = None

    # Data configuration
    max_seq_length: int = 2048
    dataset_cache_dir: Optional[str] = None
    preprocessing_num_workers: int = 4

    # PEFT configuration
    peft_type: str = "LORA"
    use_rslora: bool = True
    use_dora: bool = False
    lora_init_method: str = "default"

    def to_dict(self) -> Dict:
        """Convert config to a dictionary for serialization.

        Returns:
            Dict of all configuration parameters.
        """
        return {
            "base_model_name": self.base_model_name,
            "model_max_length": self.model_max_length,
            "torch_dtype": self.torch_dtype,
            "lora_rank": self.lora_rank,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "learning_rate": self.learning_rate,
            "num_train_epochs": self.num_train_epochs,
            "per_device_train_batch_size": self.per_device_train_batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "target_modules": self.target_modules,
            "use_rslora": self.use_rslora,
            "use_dora": self.use_dora,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "LoRAConfig":
        """Create config from a dictionary.

        Args:
            data: Dictionary of configuration parameters.

        Returns:
            LoRAConfig instance.
        """
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })


@dataclass
class TrainingRunConfig:
    """Configuration for a complete training run.

    Tracks metadata about a training run including experiment name,
    dataset used, and tracking information.
    """

    experiment_name: str = "contract-risk-lora"
    dataset_name: str = "cuad_contract_risk"
    dataset_split: str = "train"
    validation_split: str = "validation"
    test_split: str = "test"
    seed: int = 42
    data_seed: int = 42
    do_train: bool = True
    do_eval: bool = True
    do_predict: bool = True

    # Augmented CUAD-specific settings
    include_risk_labels: bool = True
    include_severity_scores: bool = True
    include_rationale: bool = True
    max_train_samples: Optional[int] = None
    max_eval_samples: Optional[int] = None

    # Output
    output_dir: str = "./outputs/contract-risk-lora"
    hub_model_id: Optional[str] = None
    push_to_hub: bool = False
