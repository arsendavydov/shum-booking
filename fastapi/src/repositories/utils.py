"""
Утилиты для репозиториев.

Содержит общие функции для работы с пагинацией, фильтрацией и другими операциями,
которые используются в нескольких репозиториях.
"""

from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import func

if TYPE_CHECKING:
    from sqlalchemy.sql.selectable import Select as SelectType


def calculate_offset(page: int, per_page: int) -> int:
    """
    Вычислить offset для пагинации.

    Args:
        page: Номер страницы (начиная с 1)
        per_page: Количество элементов на странице

    Returns:
        Значение offset для SQL запроса
    """
    return (page - 1) * per_page


def apply_pagination(query: "SelectType[Any]", page: int, per_page: int) -> "SelectType[Any]":
    """
    Применить пагинацию к SQL запросу.

    Args:
        query: SQLAlchemy Select запрос
        page: Номер страницы (начиная с 1)
        per_page: Количество элементов на странице

    Returns:
        Запрос с примененной пагинацией
    """
    offset = calculate_offset(page, per_page)
    return query.limit(per_page).offset(offset)


def apply_text_filter(query: "SelectType[Any]", field: Any, value: str) -> "SelectType[Any]":
    """
    Применить фильтр по строковому полю с частичным совпадением без учета регистра.

    Args:
        query: SQLAlchemy Select запрос
        field: Поле модели для фильтрации
        value: Значение для поиска (частичное совпадение)

    Returns:
        Запрос с примененным фильтром
    """
    return query.where(func.lower(field).contains(func.lower(value)))


def check_date_overlap(date_from1: date, date_to1: date, date_from2: date, date_to2: date) -> bool:
    """
    Проверить, пересекаются ли два периода дат.

    Два периода пересекаются, если:
    - date_from1 < date_to2 И
    - date_to1 > date_from2

    Args:
        date_from1: Дата начала первого периода
        date_to1: Дата окончания первого периода
        date_from2: Дата начала второго периода
        date_to2: Дата окончания второго периода

    Returns:
        True если периоды пересекаются, False иначе
    """
    return date_from1 < date_to2 and date_to1 > date_from2
