import pytest
from run.user_manager import UserManager
from unittest.mock import patch

# User Manager fixture
@pytest.fixture
def user_manager():
    return UserManager()


def test_add_exchange(user_manager, monkeypatch, db_session):
    mock_exchange = {'key': 'value'}
    mock_result = 1

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_exchange(mock_exchange)
        assert result == mock_result
        mock_run_default.assert_called_once()


def test_add_params_to_strategy(user_manager):
    mock_strategy = "strategy_name"
    mock_params = {'key': 'value'}
    mock_result = True

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_params_to_strategy(mock_strategy, mock_params)
        assert result == mock_result
        mock_run_default.assert_called_once()


def test_add_feed_to_bot(user_manager):
    mock_feed = {'bot_id': 1, 'key': 'value'}
    mock_result = True

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_feed_to_bot(mock_feed)
        assert result == mock_result
        mock_run_default.assert_called_once()


def test_add_bot(user_manager):
    mock_bot = {'key': 'value'}
    mock_result = 1

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_bot(mock_bot)
        assert result == mock_result
        mock_run_default.assert_called_once()


def test_add_bot_exchange(user_manager):
    mock_bot_id = 1
    mock_exchange = {'key': 'value'}
    mock_result = True

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_bot_exchange(mock_bot_id, mock_exchange)
        assert result == mock_result
        mock_run_default.assert_called_once()


def test_user_set_secret_key(user_manager):
    user_id = 'pytest'
    key = "key1"
    exchange = "kraken"
    secret = "secret"
    res = user_manager.set_secret_key(user_id=user_id,
                                      exchange=exchange,
                                      key=key,
                                      secret=secret)
    assert res is True
    key = "key2"
    exchange = "kucoin"
    res = user_manager.set_secret_key(user_id=user_id,
                                      exchange=exchange,
                                      key=key,
                                      secret=secret)
    assert res is True
    key = "key2"
    exchange = "kucoin"
    res = user_manager.set_secret_key(user_id=user_id,
                                      exchange=exchange,
                                      key=key,
                                      secret=secret)
    assert res is True
    exchange = "kraken"
    res = user_manager.del_secret_key(user_id=user_id,
                                      exchange=exchange)
    assert res is True
    exchange = "kraken"
    res = user_manager.del_secret_key(user_id=user_id,
                                      exchange=exchange)
    assert res is False
    exchange = "kucoin"
    res = user_manager.del_secret_key(user_id=user_id,
                                      exchange=exchange)
    assert res is True


def test_get_user_id(user_manager):
    user = user_manager.get_user_id(mail='admin@fullon')
    assert isinstance(user, str)


def test_user_list(user_manager):
    users = user_manager.list_users(page=1, page_size=10, all=False)
    assert isinstance(users, list)


def test_get_user_exchange(user_manager):
    uid = user_manager.get_user_id(mail='admin@fullon')
    res = user_manager.get_user_exchanges(uid=uid)


def test_del_strategy(user_manager):
    res = user_manager.del_bot_strategy(bot_id=0)
    assert res is False
