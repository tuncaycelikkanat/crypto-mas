from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.execution_log_repository import ExecutionLogRepository
from crypto_mas.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/api/v1/logs", tags=["Logs"])

@router.get("/recent")
def get_recent_logs(
    db: Annotated[Session, Depends(get_db_session)],
    account_name: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    repository = ExecutionLogRepository(db)
    logs = repository.list_recent(account_name=account_name, limit=limit)

    # Return in chronological order for terminal (oldest first in the view)
    # The repo returns desc, so we reverse it
    results = []
    for log in reversed(logs):
        results.append({
            "id": log.id,
            "level": log.level,
            "stage": log.stage,
            "message": log.message,
            "created_at": log.created_at.isoformat(),
        })

    return results
