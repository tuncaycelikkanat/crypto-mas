from crypto_mas.infrastructure.db.session import check_db_connection


def test_db_connection() -> None:
    assert check_db_connection() is True
