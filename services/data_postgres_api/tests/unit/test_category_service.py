"""
Unit tests for CategoryService.

Tests business logic without database dependencies using mocked repository.
"""
import pytest
from unittest.mock import AsyncMock, Mock

from src.application.services.category_service import CategoryService
from src.domain.models.category import Category
from src.schemas.category import CategoryCreate


@pytest.fixture
def mock_repository():
    """Create mock CategoryRepository."""
    return Mock()


@pytest.fixture
def category_service(mock_repository):
    """Create CategoryService with mocked repository."""
    return CategoryService(repository=mock_repository)


@pytest.fixture
def valid_category_data():
    """Create valid CategoryCreate data."""
    return CategoryCreate(
        user_id=1,
        name="Work",
        is_default=False
    )


@pytest.fixture
def mock_category():
    """Create mock Category domain model."""
    return Category(
        id=1,
        user_id=1,
        name="Work",
        is_default=False
    )


# ============================================================================
# Test: create_category
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_category_success(category_service, mock_repository, valid_category_data, mock_category):
    """Test successful category creation when name is unique."""
    mock_repository.get_by_user_and_name = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_category)

    result = await category_service.create_category(valid_category_data)

    assert result == mock_category
    mock_repository.get_by_user_and_name.assert_called_once_with(1, "Work")
    mock_repository.create.assert_called_once_with(valid_category_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_category_duplicate_name(category_service, mock_repository, valid_category_data, mock_category):
    """Test that creating category with duplicate name raises ValueError."""
    mock_repository.get_by_user_and_name = AsyncMock(return_value=mock_category)

    with pytest.raises(ValueError, match="Category with name 'Work' already exists for user 1"):
        await category_service.create_category(valid_category_data)

    mock_repository.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_category_same_name_different_user(category_service, mock_repository, mock_category):
    """Test that same category name can exist for different users."""
    category_data_user2 = CategoryCreate(user_id=2, name="Work", is_default=False)
    mock_repository.get_by_user_and_name = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_category)

    result = await category_service.create_category(category_data_user2)

    assert result == mock_category
    mock_repository.get_by_user_and_name.assert_called_once_with(2, "Work")


# ============================================================================
# Test: bulk_create_categories
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_create_categories_all_new(category_service, mock_repository):
    """Test bulk creating categories when all names are new."""
    categories_data = [
        CategoryCreate(user_id=1, name="Work", is_default=False),
        CategoryCreate(user_id=1, name="Study", is_default=False),
        CategoryCreate(user_id=1, name="Exercise", is_default=False),
    ]
    mock_categories = [
        Category(id=1, user_id=1, name="Work", is_default=False),
        Category(id=2, user_id=1, name="Study", is_default=False),
        Category(id=3, user_id=1, name="Exercise", is_default=False),
    ]

    mock_repository.get_by_user_and_name = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(side_effect=mock_categories)

    result = await category_service.bulk_create_categories(1, categories_data)

    assert len(result) == 3
    assert result == mock_categories
    assert mock_repository.create.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_create_categories_skip_duplicates(category_service, mock_repository):
    """Test bulk creating categories skips existing duplicates."""
    categories_data = [
        CategoryCreate(user_id=1, name="Work", is_default=False),
        CategoryCreate(user_id=1, name="Study", is_default=False),
    ]
    existing_category = Category(id=1, user_id=1, name="Work", is_default=False)
    new_category = Category(id=2, user_id=1, name="Study", is_default=False)

    async def mock_get_by_user_and_name(user_id, name):
        if name == "Work":
            return existing_category
        return None

    mock_repository.get_by_user_and_name = AsyncMock(side_effect=mock_get_by_user_and_name)
    mock_repository.create = AsyncMock(return_value=new_category)

    result = await category_service.bulk_create_categories(1, categories_data)

    assert len(result) == 1
    assert result[0] == new_category
    assert mock_repository.create.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_create_categories_empty_list(category_service, mock_repository):
    """Test bulk creating with empty list returns empty list."""
    result = await category_service.bulk_create_categories(1, [])

    assert result == []
    mock_repository.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_create_categories_all_duplicates(category_service, mock_repository, mock_category):
    """Test bulk creating when all categories already exist."""
    categories_data = [
        CategoryCreate(user_id=1, name="Work", is_default=False),
        CategoryCreate(user_id=1, name="Study", is_default=False),
    ]
    mock_repository.get_by_user_and_name = AsyncMock(return_value=mock_category)

    result = await category_service.bulk_create_categories(1, categories_data)

    assert result == []
    mock_repository.create.assert_not_called()


# ============================================================================
# Test: get_user_categories
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_categories_success(category_service, mock_repository, mock_category):
    """Test retrieving all categories for user."""
    categories = [mock_category]
    mock_repository.get_all_by_user = AsyncMock(return_value=categories)

    result = await category_service.get_user_categories(user_id=1)

    assert result == categories
    mock_repository.get_all_by_user.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_categories_empty(category_service, mock_repository):
    """Test retrieving categories when user has none."""
    mock_repository.get_all_by_user = AsyncMock(return_value=[])

    result = await category_service.get_user_categories(user_id=1)

    assert result == []


# ============================================================================
# Test: get_category_by_id
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_category_by_id_found(category_service, mock_repository, mock_category):
    """Test retrieving existing category by ID."""
    mock_repository.get_by_id = AsyncMock(return_value=mock_category)

    result = await category_service.get_category_by_id(category_id=1)

    assert result == mock_category
    mock_repository.get_by_id.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_category_by_id_not_found(category_service, mock_repository):
    """Test retrieving non-existent category returns None."""
    mock_repository.get_by_id = AsyncMock(return_value=None)

    result = await category_service.get_category_by_id(category_id=999)

    assert result is None


# ============================================================================
# Test: delete_category
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_category_success(category_service, mock_repository, mock_category):
    """Test successful category deletion when business rules satisfied."""
    mock_repository.get_by_id = AsyncMock(return_value=mock_category)
    mock_repository.count_by_user = AsyncMock(return_value=2)  # Has more than 1 category
    mock_repository.delete = AsyncMock()

    await category_service.delete_category(category_id=1)

    mock_repository.delete.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_category_not_found(category_service, mock_repository):
    """Test deleting non-existent category raises ValueError."""
    mock_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Category 1 not found"):
        await category_service.delete_category(category_id=1)

    mock_repository.delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_category_last_category(category_service, mock_repository, mock_category):
    """Test that deleting last category raises ValueError."""
    mock_repository.get_by_id = AsyncMock(return_value=mock_category)
    mock_repository.count_by_user = AsyncMock(return_value=1)

    with pytest.raises(ValueError, match="Cannot delete the last category"):
        await category_service.delete_category(category_id=1)

    mock_repository.delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_category_default_category(category_service, mock_repository):
    """Test that deleting default category raises ValueError."""
    default_category = Category(id=1, user_id=1, name="Work", is_default=True)
    mock_repository.get_by_id = AsyncMock(return_value=default_category)
    mock_repository.count_by_user = AsyncMock(return_value=2)

    with pytest.raises(ValueError, match="Cannot delete default category"):
        await category_service.delete_category(category_id=1)

    mock_repository.delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_category_exactly_two_categories(category_service, mock_repository, mock_category):
    """Test that deleting category is allowed when user has exactly 2 categories."""
    mock_repository.get_by_id = AsyncMock(return_value=mock_category)
    mock_repository.count_by_user = AsyncMock(return_value=2)
    mock_repository.delete = AsyncMock()

    await category_service.delete_category(category_id=1)

    mock_repository.delete.assert_called_once_with(1)
