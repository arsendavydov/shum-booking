from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.refresh_tokens import RefreshTokenOrm
from src.repositories.base import BaseRepository


class RefreshTokensRepository(BaseRepository[RefreshTokenOrm]):
    """
    Репозиторий для работы с refresh токенами.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория refresh токенов.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, RefreshTokenOrm)

    def _to_schema(self, orm_obj: RefreshTokenOrm) -> Any:
        """
        Refresh токены не преобразуются в схемы, возвращаем ORM объект.

        Args:
            orm_obj: ORM объект refresh токена

        Returns:
            ORM объект
        """
        return orm_obj

    async def create_token(self, user_id: int, token: str, expires_at: datetime) -> RefreshTokenOrm:
        """
        Создать новый refresh токен.

        Args:
            user_id: ID пользователя
            token: Токен (хеш)
            expires_at: Время истечения токена

        Returns:
            Созданный refresh токен
        """
        refresh_token = RefreshTokenOrm(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
            is_revoked=False,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_by_token(self, token: str) -> RefreshTokenOrm | None:
        """
        Найти refresh токен по токену.

        Args:
            token: Токен для поиска

        Returns:
            Refresh токен или None если не найден
        """
        stmt = select(RefreshTokenOrm).where(
            and_(
                RefreshTokenOrm.token == token,
                ~RefreshTokenOrm.is_revoked,
                RefreshTokenOrm.expires_at > datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_token(self, token: str) -> None:
        """
        Отозвать refresh токен (пометить как revoked).

        Args:
            token: Токен для отзыва
        """
        refresh_token = await self.get_by_token(token)
        if refresh_token:
            refresh_token.is_revoked = True
            await self.session.flush()

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """
        Отозвать все refresh токены пользователя.

        Args:
            user_id: ID пользователя
        """
        stmt = select(RefreshTokenOrm).where(
            and_(
                RefreshTokenOrm.user_id == user_id,
                ~RefreshTokenOrm.is_revoked,
            )
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
        await self.session.flush()

    async def delete_expired_tokens(self) -> int:
        """
        Удалить истекшие токены из БД.

        Returns:
            Количество удаленных токенов
        """
        stmt = select(RefreshTokenOrm).where(RefreshTokenOrm.expires_at < datetime.now(UTC))
        result = await self.session.execute(stmt)
        expired_tokens = result.scalars().all()
        count = len(expired_tokens)
        for token in expired_tokens:
            await self.session.delete(token)
        await self.session.flush()
        return count
