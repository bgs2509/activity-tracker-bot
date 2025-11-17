"""AI model selector service with automatic failover and rating system.

This service manages a pool of free AI models from OpenRouter, automatically
selecting the best performing model and implementing failover with rating updates.

Architecture:
- Models are loaded from data/ai-models.json with initial reliability ratings
- If a model fails or times out, its rating is decreased
- The next best model is automatically selected
- Ratings persist across service restarts (via Docker volume)
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
    2. Best model is tried first with 10-second timeout
    3. On failure, rating is decreased and next model is tried
    4. Ratings are persisted to disk after each update

    The service ensures fault tolerance by automatically switching to backup
    models when the primary model is unavailable or slow.

    Error handling strategy:
    - Critical errors (404, 400, 403): Model disabled (rating = 0)
    - Rate limit (429): Significant penalty (rating -= 20)
    - Timeout: Minor penalty (rating -= 5)
    - Other errors: Default penalty (rating -= 10)
    - Success: Small bonus (rating += 2, max 100)
    - Models with rating < 20 are excluded from selection
    """

    # Minimum rating threshold - models below this won't be used
    MIN_RATING_THRESHOLD = 20

    def __init__(self, models_file_path: str = "data/ai-models.json"):
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
            "google/gemini-2.0-flash-exp:free": 100,
            "google/gemma-3-27b-it:free": 95,
            "meta-llama/llama-3.2-3b-instruct:free": 90,
            "mistralai/mistral-small-3.1-24b-instruct:free": 85,
            "deepseek/deepseek-r1:free": 80,
            "qwen/qwen2.5-vl-72b-instruct:free": 80,
            "meta-llama/llama-3.2-11b-vision-instruct:free": 78,
            "google/gemma-3-12b-it:free": 75,
            "qwen/qwen2.5-vl-32b-instruct:free": 73,
            "google/gemma-2.5-flash-lite:free": 70,
            "microsoft/phi-3-mini-128k-instruct:free": 68,
            "meta-llama/llama-3.2-1b-instruct:free": 65,
            "google/gemma-3-4b-it:free": 63,
            "google/gemma-2-2b-it:free": 60,
            "nousresearch/hermes-3-llama-3.1-405b:free": 58,
            "qwen/qwen-2-7b-instruct:free": 55,
            "mistralai/mistral-7b-instruct:free": 53,
            "moonshotai/kimi-vl-a3b-thinking:free": 50,
            "liquid/lfm-40b:free": 48,
            "openchat/openchat-7b:free": 45,
            "meta-llama/llama-3.1-8b-instruct:free": 43,
            "meta-llama/llama-3-8b-instruct:free": 40,
            "google/gemini-flash-1.5:free": 38,
            "cohere/command-r-plus:free": 35,
            "cohere/command-r:free": 33,
            "anthropic/claude-3-haiku:free": 30,
            "huggingfaceh4/zephyr-7b-beta:free": 28,
            "mistralai/mixtral-8x7b-instruct:free": 25
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

        Only considers models with rating >= MIN_RATING_THRESHOLD.

        Returns:
            Model identifier (e.g., "meta-llama/llama-3.2-3b-instruct:free")

        Raises:
            RuntimeError: If no models are available
        """
        if not self.models:
            raise RuntimeError("No AI models available")

        # Filter models by minimum rating threshold
        available_models = {
            k: v for k, v in self.models.items()
            if v >= self.MIN_RATING_THRESHOLD
        }

        if not available_models:
            logger.error(
                "No AI models available above minimum threshold",
                extra={
                    "threshold": self.MIN_RATING_THRESHOLD,
                    "total_models": len(self.models)
                }
            )
            raise RuntimeError("No AI models available above minimum threshold")

        sorted_models = sorted(
            available_models.items(),
            key=lambda x: x[1],
            reverse=True
        )

        best_model = sorted_models[0][0]

        logger.debug(
            "Selected best AI model",
            extra={
                "model": best_model,
                "rating": self.models[best_model],
                "available_models": len(available_models)
            }
        )

        return best_model

    def get_next_model(
        self,
        failed_model: str,
        decrease_rating: bool = True
    ) -> str | None:
        """Get next best model after current one failed.

        This method is called when a model times out or returns an error.
        Returns the next best alternative that meets the minimum rating threshold.

        Args:
            failed_model: Model that failed or timed out
            decrease_rating: If True, apply default penalty (for backward compatibility)

        Returns:
            Next best model identifier, or None if no alternatives available
        """
        # Apply default penalty if requested (backward compatibility)
        if decrease_rating:
            self.decrease_rating(failed_model)

        # Get all models except the failed one and above threshold
        available_models = {
            k: v for k, v in self.models.items()
            if k != failed_model and v >= self.MIN_RATING_THRESHOLD
        }

        if not available_models:
            logger.warning(
                "No alternative AI models available above threshold",
                extra={
                    "failed_model": failed_model,
                    "threshold": self.MIN_RATING_THRESHOLD
                }
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
                "rating": self.models[next_model],
                "available_models": len(available_models)
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

    def increase_rating(self, model: str, bonus: int = 2) -> None:
        """Increase model's reliability rating after successful response.

        This rewards models that perform well. Rating is capped at 100.
        Bonus is kept small (2) to prevent rapid rating fluctuations.

        Args:
            model: Model identifier
            bonus: Rating increase amount (default: 2)
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

    def disable_model(self, model: str, reason: str = "") -> None:
        """Permanently disable a model by setting its rating to 0.

        Used for critical errors like 404 (model not found) or 400 (bad request).
        These models will never be selected again.

        Args:
            model: Model identifier
            reason: Reason for disabling (for logging)
        """
        if model not in self.models:
            logger.warning(
                "Attempted to disable unknown model",
                extra={"model": model}
            )
            return

        old_rating = self.models[model]
        self.models[model] = 0

        logger.warning(
            "AI model permanently disabled",
            extra={
                "model": model,
                "old_rating": old_rating,
                "reason": reason
            }
        )

        self._save_models()

    def decrease_rating_by_error_type(
        self,
        model: str,
        error_type: str,
        error_code: int | None = None
    ) -> None:
        """Decrease model rating based on error type.

        Different errors have different penalties:
        - 404, 400, 403: Permanent disable (rating = 0)
        - 429 (rate limit): Moderate penalty (-5)
        - Timeout: Minor penalty (-3)
        - Other errors: Default penalty (-10)

        Args:
            model: Model identifier
            error_type: Type of error (e.g., "NotFoundError", "RateLimitError")
            error_code: HTTP error code if applicable
        """
        if model not in self.models:
            logger.warning(
                "Attempted to decrease rating of unknown model",
                extra={"model": model}
            )
            return

        old_rating = self.models[model]

        # Determine penalty based on error type
        if error_type in ("NotFoundError", "BadRequestError", "PermissionDeniedError"):
            # Critical errors - permanently disable
            self.disable_model(
                model,
                reason=f"{error_type} (code: {error_code})"
            )
            return

        elif error_type == "RateLimitError" or error_code == 429:
            # Temporary rate limit - significant penalty to quickly rotate to alternatives
            penalty = 20
            reason = "rate limit"

        elif error_type == "TimeoutError":
            # Timeout - minor penalty
            penalty = 5
            reason = "timeout"

        else:
            # Other errors - default penalty
            penalty = 10
            reason = f"error: {error_type}"

        self.models[model] = max(0, self.models[model] - penalty)

        logger.info(
            "Decreased AI model rating",
            extra={
                "model": model,
                "old_rating": old_rating,
                "new_rating": self.models[model],
                "penalty": penalty,
                "reason": reason,
                "error_type": error_type
            }
        )

        self._save_models()

    def get_all_models(self) -> Dict[str, int]:
        """Get all models with their current ratings.

        Returns:
            Dictionary mapping model identifiers to ratings
        """
        return self.models.copy()
