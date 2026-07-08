import json
from unittest.mock import MagicMock

from crypto_mas.services.config_service.config_service import ConfigService

def test_get_config_from_redis():
    db_mock = MagicMock()
    redis_mock = MagicMock()
    
    redis_mock.get.return_value = '{"mode": "test"}'
    
    service = ConfigService(db=db_mock, redis=redis_mock)
    service.repository = MagicMock()
    config = service.get_config("bot_config")
    
    assert config == {"mode": "test"}
    redis_mock.get.assert_called_once_with("config:bot_config")
    service.repository.get_active_config.assert_not_called()

def test_get_config_from_db_when_redis_empty():
    db_mock = MagicMock()
    redis_mock = MagicMock()
    
    redis_mock.get.return_value = None
    
    active_config_mock = MagicMock()
    active_config_mock.config_json = {"mode": "db_test"}
    
    service = ConfigService(db=db_mock, redis=redis_mock)
    service.repository = MagicMock()
    service.repository.get_active_config.return_value = active_config_mock
    
    config = service.get_config("bot_config")
    
    assert config == {"mode": "db_test"}
    redis_mock.get.assert_called_once_with("config:bot_config")
    service.repository.get_active_config.assert_called_once_with("bot_config")
    redis_mock.set.assert_called_once_with("config:bot_config", '{"mode": "db_test"}', ex=300)

def test_get_config_no_redis():
    db_mock = MagicMock()
    
    active_config_mock = MagicMock()
    active_config_mock.config_json = {"mode": "db_test_no_redis"}
    
    service = ConfigService(db=db_mock)
    service.repository = MagicMock()
    service.repository.get_active_config.return_value = active_config_mock
    
    config = service.get_config("bot_config")
    
    assert config == {"mode": "db_test_no_redis"}
    service.repository.get_active_config.assert_called_once_with("bot_config")

def test_get_config_not_found():
    db_mock = MagicMock()
    service = ConfigService(db=db_mock)
    service.repository = MagicMock()
    service.repository.get_active_config.return_value = None
    
    config = service.get_config("bot_config")
    assert config is None

def test_set_active_version():
    db_mock = MagicMock()
    redis_mock = MagicMock()
    
    service = ConfigService(db=db_mock, redis=redis_mock)
    service.repository = MagicMock()
    service.set_active_version("bot_config", "v2")
    
    service.repository.set_active.assert_called_once_with("bot_config", "v2")
    redis_mock.delete.assert_called_once_with("config:bot_config")

def test_set_active_version_no_redis():
    db_mock = MagicMock()
    
    service = ConfigService(db=db_mock)
    service.repository = MagicMock()
    service.set_active_version("bot_config", "v2")
    
    service.repository.set_active.assert_called_once_with("bot_config", "v2")
