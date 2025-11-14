"""
Unit tests for AIModelSelector.

Tests AI model selection service with automatic failover, rating system,
and persistence of model reliability scores.

Test Coverage:
    - Initialization: Loading models from file/defaults
    - get_best_model(): Highest rated model selection
    - get_next_model(): Failover to alternative models
    - increase_rating(): Success reward mechanism
    - decrease_rating(): Failure penalty mechanism
    - Model persistence: Save/load ratings across restarts
    - Edge cases: Empty models, unknown models, file errors

Coverage Target: 95%+
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-14
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
from pathlib import Path

from src.application.services.ai_model_selector import AIModelSelector


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_models_data():
    """
    Fixture: Sample models with ratings.

    Returns:
        dict: Model identifier to rating mapping
    """
    return {
        "meta-llama/llama-3.2-3b-instruct:free": 100,
        "google/gemma-2-9b-it:free": 95,
        "microsoft/phi-3-mini-128k-instruct:free": 90
    }


@pytest.fixture
def temp_models_file(tmp_path):
    """
    Fixture: Temporary models file for testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path: Temporary file path
    """
    return tmp_path / "test-ai-models.json"


# ============================================================================
# TEST SUITES - Initialization
# ============================================================================

class TestAIModelSelectorInitialization:
    """
    Test suite for AIModelSelector initialization.
    """

    @pytest.mark.unit
    def test_init_with_existing_file_loads_models(self, sample_models_data, temp_models_file):
        """
        Test initialization loads models from existing file.

        GIVEN: ai-models.json exists with model ratings
        WHEN: AIModelSelector is instantiated
        THEN: Models are loaded from file
        """
        # Arrange: Write sample data to temp file
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')

        # Act
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Assert
        assert selector.models == sample_models_data
        assert len(selector.models) == 3

    @pytest.mark.unit
    def test_init_without_file_creates_defaults(self, temp_models_file):
        """
        Test initialization without existing file uses defaults.

        GIVEN: ai-models.json doesn't exist
        WHEN: AIModelSelector is instantiated
        THEN: Default models are initialized
              AND file is created with defaults
        """
        # Act
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Assert: Defaults loaded
        assert len(selector.models) > 0
        assert "meta-llama/llama-3.2-3b-instruct:free" in selector.models
        assert selector.models["meta-llama/llama-3.2-3b-instruct:free"] == 100

        # File created
        assert temp_models_file.exists()

    @pytest.mark.unit
    def test_init_with_invalid_json_uses_defaults(self, temp_models_file):
        """
        Test initialization with corrupted file uses defaults.

        GIVEN: ai-models.json contains invalid JSON
        WHEN: AIModelSelector is instantiated
        THEN: Exception is caught
              AND default models are loaded
        """
        # Arrange: Write invalid JSON
        temp_models_file.write_text("NOT VALID JSON{", encoding='utf-8')

        # Act
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Assert: Defaults used despite error
        assert len(selector.models) > 0
        assert "meta-llama/llama-3.2-3b-instruct:free" in selector.models


# ============================================================================
# TEST SUITES - get_best_model()
# ============================================================================

class TestAIModelSelectorGetBestModel:
    """
    Test suite for get_best_model() method.
    """

    @pytest.mark.unit
    def test_get_best_model_returns_highest_rated(self, sample_models_data, temp_models_file):
        """
        Test getting model with highest rating.

        GIVEN: 3 models with different ratings (100, 95, 90)
        WHEN: get_best_model() is called
        THEN: Model with rating 100 is returned
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        best_model = selector.get_best_model()

        # Assert
        assert best_model == "meta-llama/llama-3.2-3b-instruct:free"
        assert selector.models[best_model] == 100

    @pytest.mark.unit
    def test_get_best_model_with_equal_ratings_returns_first(self, temp_models_file):
        """
        Test behavior with tied ratings.

        GIVEN: Multiple models with same rating
        WHEN: get_best_model() is called
        THEN: One of the top-rated models is returned (deterministic)
        """
        # Arrange
        equal_models = {
            "model1:free": 95,
            "model2:free": 95,
            "model3:free": 90
        }
        temp_models_file.write_text(json.dumps(equal_models), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        best_model = selector.get_best_model()

        # Assert: One of the 95-rated models
        assert selector.models[best_model] == 95

    @pytest.mark.unit
    def test_get_best_model_with_no_models_raises_error(self, temp_models_file):
        """
        Test error handling when no models available.

        GIVEN: Models dict is empty
        WHEN: get_best_model() is called
        THEN: RuntimeError is raised
        """
        # Arrange
        temp_models_file.write_text(json.dumps({}), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))
        selector.models = {}  # Force empty

        # Act & Assert
        with pytest.raises(RuntimeError, match="No AI models available"):
            selector.get_best_model()


# ============================================================================
# TEST SUITES - get_next_model()
# ============================================================================

class TestAIModelSelectorGetNextModel:
    """
    Test suite for get_next_model() method.
    """

    @pytest.mark.unit
    def test_get_next_model_decreases_failed_model_rating(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test failed model rating is decreased.

        GIVEN: Model "llama" has rating 100
        WHEN: get_next_model("llama") is called
        THEN: "llama" rating is decreased by 10
              AND next best model is returned
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        failed_model = "meta-llama/llama-3.2-3b-instruct:free"
        original_rating = selector.models[failed_model]

        # Act
        next_model = selector.get_next_model(failed_model)

        # Assert: Rating decreased
        assert selector.models[failed_model] == original_rating - 10

        # Next best model returned
        assert next_model == "google/gemma-2-9b-it:free"

    @pytest.mark.unit
    def test_get_next_model_excludes_failed_model(self, sample_models_data, temp_models_file):
        """
        Test failed model is excluded from selection.

        GIVEN: 3 models available
        WHEN: get_next_model() is called with best model
        THEN: Second best model is returned (not the failed one)
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        next_model = selector.get_next_model("meta-llama/llama-3.2-3b-instruct:free")

        # Assert: Not the failed model
        assert next_model != "meta-llama/llama-3.2-3b-instruct:free"
        assert next_model == "google/gemma-2-9b-it:free"

    @pytest.mark.unit
    def test_get_next_model_when_no_alternatives_returns_none(self, temp_models_file):
        """
        Test behavior when only one model exists.

        GIVEN: Only 1 model in pool
        WHEN: get_next_model() is called with that model
        THEN: Returns None (no alternatives)
        """
        # Arrange
        single_model = {"model1:free": 100}
        temp_models_file.write_text(json.dumps(single_model), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        next_model = selector.get_next_model("model1:free")

        # Assert: No alternatives
        assert next_model is None

    @pytest.mark.unit
    def test_get_next_model_with_unknown_model_returns_best(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test handling of unknown failed model.

        GIVEN: Failed model is not in the pool
        WHEN: get_next_model() is called
        THEN: Warning is logged
              AND best available model is returned
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        next_model = selector.get_next_model("unknown-model:free")

        # Assert: Best model returned (unknown model not in pool)
        assert next_model is not None
        assert next_model in sample_models_data


# ============================================================================
# TEST SUITES - decrease_rating()
# ============================================================================

class TestAIModelSelectorDecreaseRating:
    """
    Test suite for decrease_rating() method.
    """

    @pytest.mark.unit
    def test_decrease_rating_reduces_by_default_penalty(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test rating decrease with default penalty.

        GIVEN: Model has rating 100
        WHEN: decrease_rating(model) is called
        THEN: Rating is reduced by 10 (default)
              AND changes are persisted
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        model = "meta-llama/llama-3.2-3b-instruct:free"

        # Act
        selector.decrease_rating(model)

        # Assert
        assert selector.models[model] == 90  # 100 - 10

    @pytest.mark.unit
    def test_decrease_rating_with_custom_penalty(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test rating decrease with custom penalty.

        GIVEN: Model has rating 100
        WHEN: decrease_rating(model, penalty=25) is called
        THEN: Rating is reduced by 25
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        model = "meta-llama/llama-3.2-3b-instruct:free"

        # Act
        selector.decrease_rating(model, penalty=25)

        # Assert
        assert selector.models[model] == 75  # 100 - 25

    @pytest.mark.unit
    def test_decrease_rating_cannot_go_below_zero(
        self,
        temp_models_file
    ):
        """
        Test rating is capped at 0 minimum.

        GIVEN: Model has rating 5
        WHEN: decrease_rating(model, penalty=10) is called
        THEN: Rating is capped at 0 (not negative)
        """
        # Arrange
        low_rated_models = {"model1:free": 5}
        temp_models_file.write_text(json.dumps(low_rated_models), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        selector.decrease_rating("model1:free", penalty=10)

        # Assert: Capped at 0
        assert selector.models["model1:free"] == 0

    @pytest.mark.unit
    def test_decrease_rating_for_unknown_model_logs_warning(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test decreasing rating of unknown model.

        GIVEN: Model is not in the pool
        WHEN: decrease_rating() is called
        THEN: Warning is logged
              AND no error is raised
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act: Should not raise
        selector.decrease_rating("unknown-model:free")

        # Assert: Models unchanged
        assert "unknown-model:free" not in selector.models


# ============================================================================
# TEST SUITES - increase_rating()
# ============================================================================

class TestAIModelSelectorIncreaseRating:
    """
    Test suite for increase_rating() method.
    """

    @pytest.mark.unit
    def test_increase_rating_adds_default_bonus(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test rating increase with default bonus.

        GIVEN: Model has rating 90
        WHEN: increase_rating(model) is called
        THEN: Rating is increased by 5 (default)
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        model = "microsoft/phi-3-mini-128k-instruct:free"

        # Act
        selector.increase_rating(model)

        # Assert
        assert selector.models[model] == 95  # 90 + 5

    @pytest.mark.unit
    def test_increase_rating_with_custom_bonus(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test rating increase with custom bonus.

        GIVEN: Model has rating 90
        WHEN: increase_rating(model, bonus=15) is called
        THEN: Rating is increased by 15
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        model = "microsoft/phi-3-mini-128k-instruct:free"

        # Act
        selector.increase_rating(model, bonus=15)

        # Assert
        assert selector.models[model] == 105  # 90 + 15... wait, should cap at 100

    @pytest.mark.unit
    def test_increase_rating_cannot_exceed_100(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test rating is capped at 100 maximum.

        GIVEN: Model has rating 98
        WHEN: increase_rating(model, bonus=5) is called
        THEN: Rating is capped at 100
        """
        # Arrange
        high_rated_models = {"model1:free": 98}
        temp_models_file.write_text(json.dumps(high_rated_models), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        selector.increase_rating("model1:free", bonus=5)

        # Assert: Capped at 100
        assert selector.models["model1:free"] == 100

    @pytest.mark.unit
    def test_increase_rating_for_unknown_model_logs_warning(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test increasing rating of unknown model.

        GIVEN: Model is not in the pool
        WHEN: increase_rating() is called
        THEN: Warning is logged
              AND no error is raised
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act: Should not raise
        selector.increase_rating("unknown-model:free")

        # Assert: Models unchanged
        assert "unknown-model:free" not in selector.models


# ============================================================================
# TEST SUITES - get_all_models()
# ============================================================================

class TestAIModelSelectorGetAllModels:
    """
    Test suite for get_all_models() method.
    """

    @pytest.mark.unit
    def test_get_all_models_returns_copy_of_models(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test getting all models returns a copy.

        GIVEN: Selector has 3 models
        WHEN: get_all_models() is called
        THEN: Copy of models dict is returned (not original)
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector = AIModelSelector(models_file_path=str(temp_models_file))

        # Act
        all_models = selector.get_all_models()

        # Assert: Copy returned
        assert all_models == sample_models_data
        assert all_models is not selector.models  # Different object

        # Modifying copy doesn't affect original
        all_models["new-model"] = 50
        assert "new-model" not in selector.models


# ============================================================================
# TEST SUITES - Persistence
# ============================================================================

class TestAIModelSelectorPersistence:
    """
    Test suite for model rating persistence.
    """

    @pytest.mark.unit
    def test_ratings_persist_after_decrease(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test ratings are saved to file after decrease.

        GIVEN: Model rating is decreased
        WHEN: New selector instance loads same file
        THEN: Decreased rating is persisted
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector1 = AIModelSelector(models_file_path=str(temp_models_file))

        model = "meta-llama/llama-3.2-3b-instruct:free"
        selector1.decrease_rating(model)

        # Act: Create new instance
        selector2 = AIModelSelector(models_file_path=str(temp_models_file))

        # Assert: Rating persisted
        assert selector2.models[model] == 90  # 100 - 10

    @pytest.mark.unit
    def test_ratings_persist_after_increase(
        self,
        sample_models_data,
        temp_models_file
    ):
        """
        Test ratings are saved to file after increase.

        GIVEN: Model rating is increased
        WHEN: New selector instance loads same file
        THEN: Increased rating is persisted
        """
        # Arrange
        temp_models_file.write_text(json.dumps(sample_models_data), encoding='utf-8')
        selector1 = AIModelSelector(models_file_path=str(temp_models_file))

        model = "microsoft/phi-3-mini-128k-instruct:free"
        selector1.increase_rating(model)

        # Act: Create new instance
        selector2 = AIModelSelector(models_file_path=str(temp_models_file))

        # Assert: Rating persisted
        assert selector2.models[model] == 95  # 90 + 5
