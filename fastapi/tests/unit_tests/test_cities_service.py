"""
Unit тесты для CitiesService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions.domain import EntityAlreadyExistsError, EntityNotFoundError
from src.schemas.cities import SchemaCity
from src.services.cities import CitiesService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def cities_service(mock_session):
    """Фикстура для создания экземпляра CitiesService."""
    return CitiesService(mock_session)


@pytest.fixture
def mock_cities_repo():
    """Фикстура для создания мока репозитория городов."""
    return AsyncMock()


@pytest.fixture
def mock_countries_repo():
    """Фикстура для создания мока репозитория стран."""
    return AsyncMock()


class TestCitiesServiceCreateCity:
    """Тесты для создания городов."""

    @pytest.mark.asyncio
    async def test_create_city_success(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить успешное создание города."""
        name = "Москва"
        country_id = 1
        expected_city = SchemaCity(id=1, name=name, country_id=country_id, country=None)

        from src.schemas.countries import SchemaCountry

        mock_countries_repo._get_one_by_id_exact.return_value = SchemaCountry(id=country_id, name="Россия", iso_code="RU")
        mock_cities_repo.get_by_name_and_country_id.return_value = None
        mock_cities_repo.create.return_value = expected_city

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            result = await cities_service.create_city(name, country_id)

        assert result == expected_city
        mock_countries_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_cities_repo.get_by_name_and_country_id.assert_called_once_with(name, country_id)
        mock_cities_repo.create.assert_called_once_with(name=name, country_id=country_id)

    @pytest.mark.asyncio
    async def test_create_city_country_not_found(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить, что создание города с несуществующей страной выбрасывает исключение."""
        name = "Москва"
        country_id = 999

        mock_countries_repo._get_one_by_id_exact.return_value = None

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await cities_service.create_city(name, country_id)

        assert "Страна" in str(exc_info.value)
        mock_countries_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_cities_repo.get_by_name_and_country_id.assert_not_called()
        mock_cities_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_city_duplicate_name(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить, что создание города с существующим названием выбрасывает исключение."""
        name = "Москва"
        country_id = 1
        existing_city = SchemaCity(id=1, name=name, country_id=country_id)

        from src.schemas.countries import SchemaCountry

        mock_countries_repo._get_one_by_id_exact.return_value = SchemaCountry(id=country_id, name="Россия", iso_code="RU")
        mock_cities_repo.get_by_name_and_country_id.return_value = existing_city

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await cities_service.create_city(name, country_id)

        assert "Город" in str(exc_info.value)
        assert "название" in str(exc_info.value)
        mock_countries_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_cities_repo.get_by_name_and_country_id.assert_called_once_with(name, country_id)
        mock_cities_repo.create.assert_not_called()


class TestCitiesServiceUpdateCity:
    """Тесты для обновления городов."""

    @pytest.mark.asyncio
    async def test_update_city_success(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить успешное обновление города."""
        city_id = 1
        name = "Новое Название"
        country_id = 1
        existing_city_orm = SchemaCity(id=city_id, name="Старое Название", country_id=country_id)
        updated_city = SchemaCity(id=city_id, name=name, country_id=country_id)

        mock_cities_repo._get_one_by_id_exact.return_value = existing_city_orm
        from src.schemas.countries import SchemaCountry

        mock_countries_repo._get_one_by_id_exact.return_value = SchemaCountry(id=country_id, name="Россия", iso_code="RU")
        mock_cities_repo.get_by_name_and_country_id.return_value = None
        mock_cities_repo.edit.return_value = updated_city

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            result = await cities_service.update_city(city_id, name, country_id)

        assert result == updated_city
        mock_cities_repo._get_one_by_id_exact.assert_called_once_with(city_id)
        mock_countries_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_cities_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_city_not_found(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить, что обновление несуществующего города выбрасывает исключение."""
        city_id = 999
        name = "Новое Название"
        country_id = 1

        mock_cities_repo._get_one_by_id_exact.return_value = None

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await cities_service.update_city(city_id, name, country_id)

        assert "Город" in str(exc_info.value)
        mock_cities_repo._get_one_by_id_exact.assert_called_once_with(city_id)
        mock_cities_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_city_country_not_found(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить, что обновление города с несуществующей страной выбрасывает исключение."""
        city_id = 1
        name = "Новое Название"
        country_id = 999
        existing_city_orm = SchemaCity(id=city_id, name="Старое Название", country_id=1)

        mock_cities_repo._get_one_by_id_exact.return_value = existing_city_orm
        mock_countries_repo._get_one_by_id_exact.return_value = None

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await cities_service.update_city(city_id, name, country_id)

        assert "Страна" in str(exc_info.value)
        mock_cities_repo._get_one_by_id_exact.assert_called_once_with(city_id)
        mock_countries_repo._get_one_by_id_exact.assert_called_once_with(country_id)
        mock_cities_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_city_same_name_no_check(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить, что обновление с тем же названием и страной не проверяет уникальность."""
        city_id = 1
        name = "Москва"
        country_id = 1
        existing_city_orm = SchemaCity(id=city_id, name=name, country_id=country_id)
        updated_city = SchemaCity(id=city_id, name=name, country_id=country_id)

        mock_cities_repo._get_one_by_id_exact.return_value = existing_city_orm
        from src.schemas.countries import SchemaCountry

        mock_countries_repo._get_one_by_id_exact.return_value = SchemaCountry(id=country_id, name="Россия", iso_code="RU")
        mock_cities_repo.edit.return_value = updated_city

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            result = await cities_service.update_city(city_id, name, country_id)

        assert result == updated_city
        mock_cities_repo.get_by_name_and_country_id.assert_not_called()
        mock_cities_repo.edit.assert_called_once()


class TestCitiesServicePartialUpdateCity:
    """Тесты для частичного обновления городов."""

    @pytest.mark.asyncio
    async def test_partial_update_city_name_only(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить частичное обновление только названия."""
        city_id = 1
        name = "Новое Название"
        from src.models.cities import CitiesOrm

        existing_city_orm = CitiesOrm(id=city_id, name="Старое Название", country_id=1)
        existing_city = SchemaCity(id=city_id, name="Старое Название", country_id=1, country=None)
        updated_city = SchemaCity(id=city_id, name=name, country_id=1, country=None)

        mock_cities_repo._to_schema = lambda x: existing_city
        mock_cities_repo.get_by_name_and_country_id.return_value = None
        mock_cities_repo.edit.return_value = updated_city

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = existing_city_orm
            return result_mock

        cities_service.session.execute = mock_execute

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            result = await cities_service.partial_update_city(city_id, name=name)

        assert result == updated_city
        mock_cities_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_update_city_no_changes(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить частичное обновление без изменений."""
        city_id = 1
        from src.models.cities import CitiesOrm

        existing_city_orm = CitiesOrm(id=city_id, name="Москва", country_id=1)
        existing_city = SchemaCity(id=city_id, name="Москва", country_id=1, country=None)

        mock_cities_repo._to_schema = lambda x: existing_city

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = existing_city_orm
            return result_mock

        cities_service.session.execute = mock_execute

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            result = await cities_service.partial_update_city(city_id)

        assert result == existing_city
        mock_cities_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_update_city_not_found(self, cities_service, mock_cities_repo, mock_countries_repo):
        """Проверить, что частичное обновление несуществующего города выбрасывает исключение."""
        city_id = 999

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            return result_mock

        cities_service.session.execute = mock_execute

        with patch("src.utils.db_manager.DBManager.get_countries_repository", return_value=mock_countries_repo), patch(
            "src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await cities_service.partial_update_city(city_id, name="Новое Название")

        assert "Город" in str(exc_info.value)
        mock_cities_repo.edit.assert_not_called()

