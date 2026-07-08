from unittest.mock import MagicMock
from crypto_mas.domain.repositories.config_version_repository import ConfigVersionRepository
from crypto_mas.domain.models.config_version import ConfigVersion

def test_add_config_version():
    session_mock = MagicMock()
    repo = ConfigVersionRepository(session_mock)
    
    cv = ConfigVersion(name="bot_config", version="v1", config_json={"a": 1})
    returned = repo.add(cv)
    
    session_mock.add.assert_called_once_with(cv)
    session_mock.flush.assert_called_once()
    assert returned == cv

def test_get_active_config():
    session_mock = MagicMock()
    repo = ConfigVersionRepository(session_mock)
    
    cv_mock = MagicMock()
    session_mock.scalars.return_value.first.return_value = cv_mock
    
    returned = repo.get_active_config("bot_config")
    
    session_mock.scalars.assert_called_once()
    assert returned == cv_mock

def test_list_by_name():
    session_mock = MagicMock()
    repo = ConfigVersionRepository(session_mock)
    
    cv_list = [MagicMock(), MagicMock()]
    session_mock.scalars.return_value.all.return_value = cv_list
    
    returned = repo.list_by_name("bot_config", limit=5)
    
    session_mock.scalars.assert_called_once()
    assert returned == cv_list

def test_set_active():
    session_mock = MagicMock()
    repo = ConfigVersionRepository(session_mock)
    
    repo.set_active("bot_config", "v2")
    
    assert session_mock.execute.call_count == 2
    session_mock.flush.assert_called_once()
