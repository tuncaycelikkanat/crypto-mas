from unittest.mock import MagicMock, patch

from crypto_mas.infrastructure.cache.redis_client import check_redis_connection, get_redis_client


@patch("crypto_mas.infrastructure.cache.redis_client.Redis")
def test_get_redis_client(mock_redis):
    client = get_redis_client()
    mock_redis.from_url.assert_called_once()
    assert client == mock_redis.from_url.return_value

@patch("crypto_mas.infrastructure.cache.redis_client.get_redis_client")
def test_check_redis_connection_success(mock_get_client):
    client_mock = MagicMock()
    client_mock.ping.return_value = True
    mock_get_client.return_value = client_mock
    
    assert check_redis_connection() is True
    client_mock.ping.assert_called_once()

@patch("crypto_mas.infrastructure.cache.redis_client.get_redis_client")
def test_check_redis_connection_failure(mock_get_client):
    mock_get_client.side_effect = Exception("Connection error")
    
    assert check_redis_connection() is False
