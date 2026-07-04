from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from crypto_mas.domain.models.config_version import ConfigVersion


class ConfigVersionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, config_version: ConfigVersion) -> ConfigVersion:
        self.session.add(config_version)
        self.session.flush()
        return config_version

    def get_active_config(self, name: str) -> ConfigVersion | None:
        stmt = (
            select(ConfigVersion)
            .where(ConfigVersion.name == name)
            .where(ConfigVersion.is_active == True)
            .order_by(ConfigVersion.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_by_name(self, name: str, limit: int = 10) -> Sequence[ConfigVersion]:
        stmt = (
            select(ConfigVersion)
            .where(ConfigVersion.name == name)
            .order_by(ConfigVersion.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()

    def set_active(self, name: str, version: str) -> None:
        # Deactivate all
        deactivate_stmt = (
            update(ConfigVersion)
            .where(ConfigVersion.name == name)
            .values(is_active=False)
        )
        self.session.execute(deactivate_stmt)

        # Activate specific
        activate_stmt = (
            update(ConfigVersion)
            .where(ConfigVersion.name == name)
            .where(ConfigVersion.version == version)
            .values(is_active=True)
        )
        self.session.execute(activate_stmt)
        self.session.flush()
