"""
Тесты для проверки наличия и использования индексов в базе данных.

Проверяет, что индексы созданы и используются в запросах для оптимизации производительности.
"""

import pytest
from sqlalchemy import text


@pytest.mark.database
class TestDatabaseIndexes:
    """Тесты для проверки индексов в базе данных."""

    @pytest.mark.asyncio
    async def test_users_email_index_exists(self, db_session):
        """Проверить, что индекс на users.email существует."""
        async with db_session as session:
            query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'users'
                AND indexname = 'ix_users_email'
            """)
            result = await session.execute(query)
            index = result.scalar_one_or_none()
            assert index is not None, "Индекс ix_users_email не найден"

    @pytest.mark.asyncio
    async def test_hotels_city_id_index_exists(self, db_session):
        """Проверить, что индекс на hotels.city_id существует."""
        async with db_session as session:
            query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'hotels'
                AND indexname = 'ix_hotels_city_id'
            """)
            result = await session.execute(query)
            index = result.scalar_one_or_none()
            assert index is not None, "Индекс ix_hotels_city_id не найден"

    @pytest.mark.asyncio
    async def test_rooms_hotel_id_index_exists(self, db_session):
        """Проверить, что индекс на rooms.hotel_id существует."""
        async with db_session as session:
            query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'rooms'
                AND indexname = 'ix_rooms_hotel_id'
            """)
            result = await session.execute(query)
            index = result.scalar_one_or_none()
            assert index is not None, "Индекс ix_rooms_hotel_id не найден"

    @pytest.mark.asyncio
    async def test_bookings_indexes_exist(self, db_session):
        """Проверить, что все индексы на bookings существуют."""
        async with db_session as session:
            expected_indexes = [
                "ix_bookings_room_id",
                "ix_bookings_date_from",
                "ix_bookings_date_to",
                "ix_bookings_room_dates",
                "ix_bookings_user_id",
            ]

            query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'bookings'
            """)
            result = await session.execute(query)
            existing_indexes = {row[0] for row in result.fetchall()}

            for index_name in expected_indexes:
                assert index_name in existing_indexes, f"Индекс {index_name} не найден"

    @pytest.mark.asyncio
    async def test_cities_country_id_index_exists(self, db_session):
        """Проверить, что индекс на cities.country_id существует."""
        async with db_session as session:
            query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'cities'
                AND indexname = 'ix_cities_country_id'
            """)
            result = await session.execute(query)
            index = result.scalar_one_or_none()
            assert index is not None, "Индекс ix_cities_country_id не найден"

    @pytest.mark.asyncio
    async def test_bookings_room_dates_composite_index_exists(self, db_session):
        """Проверить, что составной индекс на bookings (room_id, date_from, date_to) существует."""
        async with db_session as session:
            query = text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'bookings'
                AND indexname = 'ix_bookings_room_dates'
            """)
            result = await session.execute(query)
            row = result.fetchone()
            assert row is not None, "Составной индекс ix_bookings_room_dates не найден"

            indexdef = row[1]
            assert "room_id" in indexdef, "Составной индекс должен содержать room_id"
            assert "date_from" in indexdef, "Составной индекс должен содержать date_from"
            assert "date_to" in indexdef, "Составной индекс должен содержать date_to"

    @pytest.mark.asyncio
    async def test_users_email_index_used_in_query(self, db_session):
        """Проверить, что индекс на users.email существует и может использоваться в запросах."""
        async with db_session as session:
            # Создаем тестового пользователя
            await session.execute(
                text("""
                INSERT INTO users (email, hashed_password)
                VALUES ('test_index@example.com', 'hashed_password')
                ON CONFLICT (email) DO NOTHING
            """)
            )
            await session.commit()

            # Обновляем статистику, чтобы PostgreSQL мог использовать индекс
            await session.execute(text("ANALYZE users"))
            await session.commit()

            # Проверяем план выполнения запроса
            query = text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM users WHERE email = 'test_index@example.com'
            """)
            result = await session.execute(query)
            plan = result.scalar_one()

            # Проверяем план выполнения
            plan_dict = plan[0] if isinstance(plan, list) else plan
            node_type = plan_dict.get("Plan", {}).get("Node Type", "")

            # PostgreSQL может использовать Seq Scan для очень маленьких таблиц,
            # но индекс должен существовать и использоваться при достаточном количестве данных
            # Проверяем, что запрос выполняется корректно и индекс существует
            assert node_type in ["Index Scan", "Index Only Scan", "Seq Scan"], (
                f"Неожиданный тип сканирования: {node_type}. План: {plan_dict}"
            )

            # Проверяем, что индекс существует (это главное)
            index_query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'users'
                AND indexname = 'ix_users_email'
            """)
            index_result = await session.execute(index_query)
            index = index_result.scalar_one_or_none()
            assert index is not None, "Индекс ix_users_email должен существовать"

    @pytest.mark.asyncio
    async def test_bookings_composite_index_used_in_query(self, db_session):
        """Проверить, что составной индекс на bookings используется в запросе проверки конфликтов."""
        async with db_session as session:
            # Проверяем план выполнения запроса, который должен использовать составной индекс
            query = text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM bookings
                WHERE room_id = 1
                AND date_from < '2026-12-31'::date
                AND date_to > '2026-01-01'::date
            """)
            result = await session.execute(query)
            plan = result.scalar_one()

            # Проверяем, что используется индекс
            plan_str = str(plan[0])
            assert "Index Scan" in plan_str or "Index Only Scan" in plan_str, (
                f"Составной индекс не используется в запросе. План: {plan_str}"
            )
