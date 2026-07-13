from unittest.mock import MagicMock, patch

from crypto_mas.infrastructure.db.session import check_db_connection, get_db_session


@patch("crypto_mas.infrastructure.db.session.SessionLocal")
def test_get_db_session(mock_session_local):
    session_mock = MagicMock()
    mock_session_local.return_value = session_mock
    
    gen = get_db_session()
    db = next(gen)
    
    assert db == session_mock
    
    try:
        next(gen)
    except StopIteration:
        pass
        
    session_mock.close.assert_called_once()

@patch("crypto_mas.infrastructure.db.session.engine")
def test_check_db_connection_success(mock_engine):
    conn_mock = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = conn_mock
    
    assert check_db_connection() is True
    conn_mock.execute.assert_called_once()

@patch("crypto_mas.infrastructure.db.session.engine")
def test_check_db_connection_failure(mock_engine):
    mock_engine.connect.side_effect = Exception("DB error")
    
    assert check_db_connection() is False
