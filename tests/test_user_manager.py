import pytest
from run.user_manager import UserManager
from unittest.mock import patch

# User Manager fixture
@pytest.fixture
def user_manager():
    return UserManager()


@pytest.mark.order(1)
def test_add_exchange(user_manager, monkeypatch, db_session):
    mock_exchange = {'key': 'value'}
    mock_result = 1

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_exchange(mock_exchange)
        assert result == mock_result
        mock_run_default.assert_called_once()

@pytest.mark.order(3)
def bot_id(uid):
    user = UserManager()
    BOT = {
        'user': uid,
        'name': 'pytest bot',
        'dry_run': 'True',
        'active': 'False'
    }
    bot_id = user.add_bot(bot=BOT)
    assert bot_id > 1
    user.remove_bot(bot_id=bot_id)


@pytest.mark.order(4)
def test_add_bot(user_manager):
    mock_bot = {'key': 'value'}
    mock_result = 1

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_bot(mock_bot)
        assert result == mock_result
        mock_run_default.assert_called_once()


@pytest.mark.order(5)
def test_add_bot_exchange(user_manager):
    mock_bot_id = 1
    mock_exchange = {'key': 'value'}
    mock_result = True

    with patch('libs.database.Database._run_default', return_value=mock_result) as mock_run_default:
        result = user_manager.add_bot_exchange(mock_bot_id, mock_exchange)
        assert result == mock_result
        mock_run_default.assert_called_once()

'''
@pytest.mark.order(6)
def test_user_set_secret_key(user_manager):
    user_id = 0
    key = "key1"
    exchange = "kraken"
    secret = "secret"
    res = user_manager.set_secret_key(user_id=user_id,
                                      exchange=exchange,
                                      key=key,
                                      secret=secret)
    assert res is True
    exchange = "kraken"
    res = user_manager.del_secret_key(user_id=user_id,
                                      exchange=exchange)
'''


@pytest.mark.order(7)
def test_get_user_id(user_manager, test_mail):
    user = user_manager.get_user_id(mail=test_mail)
    assert isinstance(user, int)


@pytest.mark.order(8)
def test_user_list(user_manager):
    users = user_manager.list_users(page=1, page_size=10, all=False)
    assert isinstance(users, list)

@pytest.mark.order(9)
def test_get_user_exchange(user_manager, test_mail, uid,  exchange1):
    _uid = user_manager.get_user_id(mail=test_mail)
    assert _uid == uid
    res = user_manager.get_user_exchanges(uid=_uid)
    assert isinstance(res, list)
    assert isinstance(res[0], dict)
    assert res[0]['cat_ex_id'] == exchange1.cat_ex_id
    _uid = user_manager.get_user_id(mail='notreal@noexists.com')
    assert _uid is None
    res = user_manager.get_user_exchanges(uid=_uid)
    assert res == []


@pytest.mark.order(10)
def test_add_and_remove_user(user_manager, dbase):
    user = {
        'mail': 'test_password',
        'password': 'test_password',
        'f2a': 'test_f2a',
        'role': 'test_role',
        'name': 'Test',
        'lastname': 'User',
        'phone': '1234567890',
        'id_num': '123456',
    }

    # Add the user
    user_manager.add_user(user)
    user_id = dbase.get_user_id(mail=user['mail'])
    assert user_id is not None
    # Remove the user
    user_manager.remove_user(user_id=user_id)
    # Check if the user was removed
    user_id_after_removal = dbase.get_user_id(mail=user['mail'])
    assert user_id_after_removal is None
