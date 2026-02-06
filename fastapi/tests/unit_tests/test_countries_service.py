"""
Unit тесты для CountriesService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions.domain import EntityAlreadyExistsError, EntityNotFoundError
from src.schemas.countries import SchemaCountry
from src.services.countries import CountriesService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def countries_service(mock_session):
    """Фикстура для создания экземпляра CountriesService."""
    return CountriesService(mock_session)


@pytest.fixture
def mock_countries_repo():
    """Фикстура для создания мока репозитория стран."""
    return AsyncMock()


class TestCountriesServiceCreateCountry:
    """Тесты для создания стран."""

    @pytest.mark.asyncio
    async def test_create_country_success(self, countries_service):
        """Проверить успешное создание страны."""
        name = "Россия"
        iso_code = "RU"
        expected_country = SchemaCountry(id=1, name=name, iso_code=iso_code.upper())

        mock_repo = AsyncMock()
        mock_repo.get_by_name_case_insensitive.return_value = None
        mock_repo.get_by_iso_code.return_value = None
        mock_repo.create.return_value = expected_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.create_country(name, iso_code)

        assert result == expected_country
        mock_repo.get_by_name_case_insensitive.assert_called_once_with(name)
        mock_repo.get_by_iso_code.assert_called_once_with(iso_code)
        mock_repo.create.assert_called_once_with(name=name, iso_code=iso_code.upper())

    @pytest.mark.asyncio
    async def test_create_country_duplicate_name(self, countries_service):
        """Проверить, что создание страны с существующим названием выбрасывает исключение."""
        name = "Россия"
        iso_code = "RU"
        existing_country = SchemaCountry(id=1, name=name, iso_code="XX")

        mock_repo = AsyncMock()
        mock_repo.get_by_name_case_insensitive.return_value = existing_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await countries_service.create_country(name, iso_code)

        assert "Страна" in str(exc_info.value)
        assert "название" in str(exc_info.value)
        mock_repo.get_by_name_case_insensitive.assert_called_once_with(name)
        mock_repo.get_by_iso_code.assert_not_called()
        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_country_duplicate_iso_code(self, countries_service):
        """Проверить, что создание страны с существующим ISO кодом выбрасывает исключение."""
        name = "Новая Страна"
        iso_code = "RU"
        existing_country = SchemaCountry(id=1, name="Россия", iso_code=iso_code)

        mock_repo = AsyncMock()
        mock_repo.get_by_name_case_insensitive.return_value = None
        mock_repo.get_by_iso_code.return_value = existing_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await countries_service.create_country(name, iso_code)

        assert "Страна" in str(exc_info.value)
        assert "ISO код" in str(exc_info.value)
        mock_repo.get_by_name_case_insensitive.assert_called_once_with(name)
        mock_repo.get_by_iso_code.assert_called_once_with(iso_code)
        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_country_iso_code_uppercase(self, countries_service):
        """Проверить, что ISO код преобразуется в верхний регистр."""
        name = "Россия"
        iso_code = "ru"
        expected_country = SchemaCountry(id=1, name=name, iso_code="RU")

        mock_repo = AsyncMock()
        mock_repo.get_by_name_case_insensitive.return_value = None
        mock_repo.get_by_iso_code.return_value = None
        mock_repo.create.return_value = expected_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.create_country(name, iso_code)

        assert result.iso_code == "RU"
        mock_repo.create.assert_called_once_with(name=name, iso_code="RU")


class TestCountriesServiceUpdateCountry:
    """Тесты для обновления стран."""

    @pytest.mark.asyncio
    async def test_update_country_success(self, countries_service):
        """Проверить успешное обновление страны."""
        country_id = 1
        name = "Новое Название"
        iso_code = "XX"
        existing_country = SchemaCountry(id=country_id, name="Старое Название", iso_code="YY")
        updated_country = SchemaCountry(id=country_id, name=name, iso_code=iso_code.upper())

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = existing_country
        mock_repo.get_by_name_case_insensitive.return_value = None
        mock_repo.get_by_iso_code.return_value = None
        mock_repo.edit.return_value = updated_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.update_country(country_id, name, iso_code)

        assert result == updated_country
        mock_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_country_not_found(self, countries_service):
        """Проверить, что обновление несуществующей страны выбрасывает исключение."""
        country_id = 999
        name = "Новое Название"
        iso_code = "XX"

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = None

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await countries_service.update_country(country_id, name, iso_code)

        assert "Страна" in str(exc_info.value)
        mock_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_country_same_name_no_check(self, countries_service):
        """Проверить, что обновление с тем же названием не проверяет уникальность."""
        country_id = 1
        name = "Россия"
        iso_code = "XX"
        existing_country = SchemaCountry(id=country_id, name=name, iso_code="YY")
        updated_country = SchemaCountry(id=country_id, name=name, iso_code=iso_code.upper())

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = existing_country
        mock_repo.get_by_iso_code.return_value = None
        mock_repo.edit.return_value = updated_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.update_country(country_id, name, iso_code)

        assert result == updated_country
        mock_repo.get_by_name_case_insensitive.assert_not_called()
        mock_repo.edit.assert_called_once()


class TestCountriesServicePartialUpdateCountry:
    """Тесты для частичного обновления стран."""

    @pytest.mark.asyncio
    async def test_partial_update_country_name_only(self, countries_service):
        """Проверить частичное обновление только названия."""
        country_id = 1
        name = "Новое Название"
        existing_country = SchemaCountry(id=country_id, name="Старое Название", iso_code="RU")
        updated_country = SchemaCountry(id=country_id, name=name, iso_code="RU")

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = existing_country
        mock_repo.get_by_name_case_insensitive.return_value = None
        mock_repo.edit.return_value = updated_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.partial_update_country(country_id, name=name)

        assert result == updated_country
        mock_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_update_country_iso_code_only(self, countries_service):
        """Проверить частичное обновление только ISO кода."""
        country_id = 1
        iso_code = "XX"
        existing_country = SchemaCountry(id=country_id, name="Россия", iso_code="RU")
        updated_country = SchemaCountry(id=country_id, name="Россия", iso_code=iso_code.upper())

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = existing_country
        mock_repo.get_by_iso_code.return_value = None
        mock_repo.edit.return_value = updated_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.partial_update_country(country_id, iso_code=iso_code)

        assert result == updated_country
        mock_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_update_country_no_changes(self, countries_service):
        """Проверить частичное обновление без изменений."""
        country_id = 1
        from src.models.countries import CountriesOrm

        existing_country_orm = CountriesOrm(id=country_id, name="Россия", iso_code="RU")
        existing_country = SchemaCountry(id=country_id, name="Россия", iso_code="RU")

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = existing_country_orm
        mock_repo._to_schema = lambda x: existing_country

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            result = await countries_service.partial_update_country(country_id)

        assert result == existing_country
        mock_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_update_country_not_found(self, countries_service):
        """Проверить, что частичное обновление несуществующей страны выбрасывает исключение."""
        country_id = 999

        mock_repo = AsyncMock()
        mock_repo._get_one_by_id_exact.return_value = None

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await countries_service.partial_update_country(country_id, name="Новое Название")

        assert "Страна" in str(exc_info.value)
        mock_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_repo.edit.assert_not_called()
