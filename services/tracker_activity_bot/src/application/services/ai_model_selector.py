"""AI model selector service with automatic failover and rating system.

This service manages a pool of free AI models from OpenRouter, automatically
selecting the best performing model and implementing failover with rating updates.

Architecture:
- Models are loaded from ai-models.json with initial reliability ratings
- If a model fails or times out, its rating is decreased
- The next best model is automatically selected
- Ratings persist across service restarts
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class AIModelSelector:
    """Manages AI model selection with automatic failover and rating updates.

    This service implements a reliability-based model selection algorithm:
    1. Models are sorted by reliability rating (0-100)
    2. Best model is tried first with 1-second timeout
    3. On failure, rating is decreased and next model is tried
    4. Ratings are persisted to disk after each update

    The service ensures fault tolerance by automatically switching to backup
    models when the primary model is unavailable or slow.
    """

    def __init__(self, models_file_path: str = "ai-models.json"):
        """Initialize model selector with models configuration file.

        Args:
            models_file_path: Path to JSON file with model ratings
        """
        self.models_file_path = Path(models_file_path)
        self.models: Dict[str, int] = {}
        self._load_models()

    def _load_models(self) -> None:
        """Load model ratings from JSON file.

        If file doesn't exist, initializes with default models.
        If file is invalid, logs error and uses defaults.
        """
        try:
            if self.models_file_path.exists():
                with open(self.models_file_path, "r", encoding="utf-8") as f:
                    self.models = json.load(f)
                logger.info(
                    "AI models loaded successfully",
                    extra={"models_count": len(self.models)}
                )
            else:
                logger.warning(
                    "AI models file not found, using defaults",
                    extra={"file_path": str(self.models_file_path)}
                )
                self._initialize_default_models()
        except Exception as e:
            logger.error(
                "Failed to load AI models, using defaults",
                extra={"error": str(e)},
                exc_info=True
            )
            self._initialize_default_models()

    def _initialize_default_models(self) -> None:
        """Initialize with default set of free OpenRouter models."""
        self.models = {
            "meta-llama/llama-3.2-3b-instruct:free": 100,
            "google/gemma-2-9b-it:free": 95,
            "microsoft/phi-3-mini-128k-instruct:free": 90,
            "meta-llama/llama-3.2-1b-instruct:free": 85,
            "google/gemma-2-2b-it:free": 80,
            "nousresearch/hermes-3-llama-3.1-405b:free": 75,
            "qwen/qwen-2-7b-instruct:free": 70,
            "mistralai/mistral-7b-instruct:free": 65,
            "liquid/lfm-40b:free": 60,
            "openchat/openchat-7b:free": 55
        }
        self._save_models()

    def _save_models(self) -> None:
        """Persist current model ratings to disk.

        This ensures ratings survive service restarts and allows the system
        to learn which models are most reliable over time.
        """
        try:
            with open(self.models_file_path, "w", encoding="utf-8") as f:
                json.dump(self.models, f, indent=2, ensure_ascii=False)
            logger.debug(
                "AI models ratings saved",
                extra={"file_path": str(self.models_file_path)}
            )
        except Exception as e:
            logger.error(
                "Failed to save AI models ratings",
                extra={"error": str(e)},
                exc_info=True
            )

    def get_best_model(self) -> str:
        """Get model with highest reliability rating.

        Returns:
            Model identifier (e.g., "meta-llama/llama-3.2-3b-instruct:free")

        Raises:
            RuntimeError: If no models are available
        """
        if not self.models:
            raise RuntimeError("No AI models available")

        sorted_models = sorted(
            self.models.items(),
            key=lambda x: x[1],
            reverse=True
        )

        best_model = sorted_models[0][0]

        logger.debug(
            "Selected best AI model",
            extra={
                "model": best_model,
                "rating": self.models[best_model]
            }
        )

        return best_model

    def get_next_model(self, failed_model: str) -> str | None:
        """Get next best model after current one failed.

        This method is called when a model times out or returns an error.
        It automatically decreases the failed model's rating and returns
        the next best alternative.

        Args:
            failed_model: Model that failed or timed out

        Returns:
            Next best model identifier, or None if no alternatives available
        """
        # Decrease rating of failed model
        self.decrease_rating(failed_model)

        # Get all models except the failed one
        available_models = {
            k: v for k, v in self.models.items()
            if k != failed_model
        }

        if not available_models:
            logger.warning(
                "No alternative AI models available",
                extra={"failed_model": failed_model}
            )
            return None

        # Get best from remaining models
        sorted_models = sorted(
            available_models.items(),
            key=lambda x: x[1],
            reverse=True
        )

        next_model = sorted_models[0][0]

        logger.info(
            "Switched to alternative AI model",
            extra={
                "failed_model": failed_model,
                "next_model": next_model,
                "rating": self.models[next_model]
            }
        )

        return next_model

    def decrease_rating(self, model: str, penalty: int = 10) -> None:
        """Decrease model's reliability rating after failure.

        This implements a learning mechanism where unreliable models
        are gradually deprioritized. Rating never goes below 0.

        Args:
            model: Model identifier
            penalty: Rating decrease amount (default: 10)
        """
        if model not in self.models:
            logger.warning(
                "Attempted to decrease rating of unknown model",
                extra={"model": model}
            )
            return

        old_rating = self.models[model]
        self.models[model] = max(0, self.models[model] - penalty)

        logger.info(
            "Decreased AI model rating",
            extra={
                "model": model,
                "old_rating": old_rating,
                "new_rating": self.models[model],
                "penalty": penalty
            }
        )

        self._save_models()

    def increase_rating(self, model: str, bonus: int = 5) -> None:
        """Increase model's reliability rating after successful response.

        This rewards models that perform well. Rating is capped at 100.

        Args:
            model: Model identifier
            bonus: Rating increase amount (default: 5)
        """
        if model not in self.models:
            logger.warning(
                "Attempted to increase rating of unknown model",
                extra={"model": model}
            )
            return

        old_rating = self.models[model]
        self.models[model] = min(100, self.models[model] + bonus)

        logger.debug(
            "Increased AI model rating",
            extra={
                "model": model,
                "old_rating": old_rating,
                "new_rating": self.models[model],
                "bonus": bonus
            }
        )

        self._save_models()

    def get_all_models(self) -> Dict[str, int]:
        """Get all models with their current ratings.

        Returns:
            Dictionary mapping model identifiers to ratings
        """
        return self.models.copy()
