from datetime import datetime

from pydantic import BaseModel


class Fold(BaseModel):
    fold_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
