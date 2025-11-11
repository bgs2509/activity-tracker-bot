"""Helper functions for category handlers.

Contains keyboard builders, validators, and utility functions.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.application.utils.validators import validate_string_length


def build_category_list_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for category list view.

    Returns:
        Inline keyboard with add/delete/menu buttons
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category")],
        [InlineKeyboardButton(text="❌ Удалить категорию", callback_data="delete_category_start")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def build_emoji_selection_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with emoji selection options.

    Returns:
        Inline keyboard with thematically grouped emoji buttons
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        # ===== ТВОРЧЕСТВО И ХОББИ =====
        [
            InlineKeyboardButton(text="🎨 Творчество", callback_data="emoji:🎨"),
            InlineKeyboardButton(text="🎵 Музыка", callback_data="emoji:🎵"),
            InlineKeyboardButton(text="📷 Фото", callback_data="emoji:📷"),
            InlineKeyboardButton(text="✏️ Рисование", callback_data="emoji:✏️"),
        ],
        [
            InlineKeyboardButton(text="🎪 Цирк", callback_data="emoji:🎪"),
            InlineKeyboardButton(text="🎭 Театр", callback_data="emoji:🎭"),
            InlineKeyboardButton(text="🎬 Кино", callback_data="emoji:🎬"),
            InlineKeyboardButton(text="🎯 Цель", callback_data="emoji:🎯"),
        ],

        # ===== СПОРТ И ЗДОРОВЬЕ =====
        [
            InlineKeyboardButton(text="🏃 Бег", callback_data="emoji:🏃"),
            InlineKeyboardButton(text="🏋️ Зал", callback_data="emoji:🏋️"),
            InlineKeyboardButton(text="🚴 Велосипед", callback_data="emoji:🚴"),
            InlineKeyboardButton(text="🧘 Йога", callback_data="emoji:🧘"),
        ],
        [
            InlineKeyboardButton(text="⚽ Футбол", callback_data="emoji:⚽"),
            InlineKeyboardButton(text="🏊 Плавание", callback_data="emoji:🏊"),
            InlineKeyboardButton(text="🥾 Поход", callback_data="emoji:🥾"),
            InlineKeyboardButton(text="💊 Здоровье", callback_data="emoji:💊"),
        ],

        # ===== ТРАНСПОРТ =====
        [
            InlineKeyboardButton(text="🚗 Машина", callback_data="emoji:🚗"),
            InlineKeyboardButton(text="✈️ Самолет", callback_data="emoji:✈️"),
            InlineKeyboardButton(text="🚇 Метро", callback_data="emoji:🚇"),
            InlineKeyboardButton(text="🚲 Велик", callback_data="emoji:🚲"),
        ],

        # ===== РАБОТА И УЧЕБА =====
        [
            InlineKeyboardButton(text="💼 Работа", callback_data="emoji:💼"),
            InlineKeyboardButton(text="📚 Книги", callback_data="emoji:📚"),
            InlineKeyboardButton(text="🎓 Учеба", callback_data="emoji:🎓"),
            InlineKeyboardButton(text="💻 Компьютер", callback_data="emoji:💻"),
        ],
        [
            InlineKeyboardButton(text="📝 Письмо", callback_data="emoji:📝"),
            InlineKeyboardButton(text="📊 Отчеты", callback_data="emoji:📊"),
            InlineKeyboardButton(text="📈 Аналитика", callback_data="emoji:📈"),
            InlineKeyboardButton(text="🔬 Наука", callback_data="emoji:🔬"),
        ],

        # ===== ДОМ И СЕМЬЯ =====
        [
            InlineKeyboardButton(text="🏠 Дом", callback_data="emoji:🏠"),
            InlineKeyboardButton(text="👨‍👩‍👧 Семья", callback_data="emoji:👨‍👩‍👧"),
            InlineKeyboardButton(text="🍳 Готовка", callback_data="emoji:🍳"),
            InlineKeyboardButton(text="🧹 Уборка", callback_data="emoji:🧹"),
        ],
        [
            InlineKeyboardButton(text="🛏️ Сон", callback_data="emoji:🛏️"),
            InlineKeyboardButton(text="🛠️ Ремонт", callback_data="emoji:🛠️"),
            InlineKeyboardButton(text="🌱 Растения", callback_data="emoji:🌱"),
            InlineKeyboardButton(text="🐕 Питомцы", callback_data="emoji:🐕"),
        ],

        # ===== ПОКУПКИ И ФИНАНСЫ =====
        [
            InlineKeyboardButton(text="🛒 Покупки", callback_data="emoji:🛒"),
            InlineKeyboardButton(text="💰 Деньги", callback_data="emoji:💰"),
            InlineKeyboardButton(text="💳 Карта", callback_data="emoji:💳"),
            InlineKeyboardButton(text="🏦 Банк", callback_data="emoji:🏦"),
        ],

        # ===== СВЯЗЬ И СОЦСЕТИ =====
        [
            InlineKeyboardButton(text="📱 Телефон", callback_data="emoji:📱"),
            InlineKeyboardButton(text="📞 Звонок", callback_data="emoji:📞"),
            InlineKeyboardButton(text="💬 Чат", callback_data="emoji:💬"),
            InlineKeyboardButton(text="📧 Email", callback_data="emoji:📧"),
        ],

        # ===== ПРОЧЕЕ =====
        [
            InlineKeyboardButton(text="⭐ Важное", callback_data="emoji:⭐"),
            InlineKeyboardButton(text="❓ Вопрос", callback_data="emoji:❓"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="emoji:⚙️"),
            InlineKeyboardButton(text="🎁 Подарок", callback_data="emoji:🎁"),
        ],

        # ===== СПЕЦИАЛЬНЫЕ ОПЦИИ =====
        [InlineKeyboardButton(text="➖ Без эмодзи", callback_data="emoji:none")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
    ])


def build_delete_category_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Build keyboard for category deletion selection.

    Args:
        categories: List of user's categories

    Returns:
        Inline keyboard with category buttons (2 per row) and navigation
    """
    buttons = []

    # Add category buttons (2 per row)
    for i, cat in enumerate(categories):
        emoji = cat.get("emoji", "")
        name = cat["name"]
        button = InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"delete_cat:{cat['id']}"
        )
        if i % 2 == 0:
            buttons.append([button])
        else:
            buttons[-1].append(button)

    # Add navigation buttons
    buttons.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="categories")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_delete_confirmation_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Build keyboard for category deletion confirmation.

    Args:
        category_id: Category ID to confirm deletion

    Returns:
        Inline keyboard with confirm/cancel buttons
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{category_id}")],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="categories")],
    ])


def build_post_creation_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard shown after successful category creation.

    Returns:
        Inline keyboard with options to add another category or navigate
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё категорию", callback_data="add_category")],
        [InlineKeyboardButton(text="📂 К списку категорий", callback_data="categories")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def build_post_deletion_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard shown after successful category deletion.

    Returns:
        Inline keyboard with navigation options
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 К списку категорий", callback_data="categories")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def validate_category_name(name: str) -> str | None:
    """Validate category name.

    Args:
        name: Category name to validate

    Returns:
        Error message if invalid, None if valid
    """
    return validate_string_length(
        value=name,
        min_length=2,
        max_length=50,
        field_name_ru="Название"
    )


def validate_emoji(emoji: str | None) -> str | None:
    """Validate emoji length.

    Args:
        emoji: Emoji string to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not emoji:
        return None

    return validate_string_length(
        value=emoji,
        max_length=10,
        field_name_ru="Эмодзи",
        allow_empty=True
    )
