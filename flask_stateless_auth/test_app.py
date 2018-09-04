import os
import json
import pytest
import tempfile

from flask import request, current_app, g
from flask_stateless_auth.app_example import db, app, stateless_auth_manager, User, ApiToken
from flask_stateless_auth import current_stateless_user, _get_stateless_user


class TestConfig():
    #AUTH_TYPE = 'Bearer'         # Default
    #AUTH_HEADER = 'Authorization'# Default
    #ADD_CONTEXT_PROCESSOR = True # Default
    ## Other configs ##
    TESTING = True
    TOKENS_BYTES_LENGTH = 32
    ACCESS_TOKEN_DEFAULT_EXPIRY = 3600 # seconds
    REFRESH_TOKEN_DEFAULT_EXPIRY = 365 # days
    SECRET_KEY = 'jd97as(DGS&(*ds8SD^GoSDO'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_FILE_DESCRIPTOR, DB_NAME = tempfile.mkstemp(dir=BASE_DIR)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DB_NAME
    SQLALCHEMY_TRACK_MODIFICATIONS = False

@pytest.fixture('session')
def client():
    config = TestConfig()
    app.config.from_object(config)
    client = app.test_client()
    db.init_app(app)
    with app.app_context():
        db.create_all()
    stateless_auth_manager.init_app(app)
    yield client
    os.close(config.DB_FILE_DESCRIPTOR)
    os.unlink(config.DB_NAME)

def test_app_is_functional(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b'hello' in res.data

def test_create_user(client):
    data = json.dumps({'username': 'test_user'})
    res = client.post('/user', data=data)
    assert res.status_code == 200
    with app.app_context():
        assert User.query.filter_by(username='test_user').first()

def create_token(client, data):
    return client.post('/create_token', data=data)

def test_token_created(client):
    data = json.dumps({'username': 'test_user'})
    res = create_token(client, data)
    assert res.status_code == 200
    token = json.loads(res.data) 
    assert token['access_token']
    assert token['refresh_token']
    assert token['expiry']
    with app.app_context():
        user = User.query.filter_by(username='test_user').first()
        assert ApiToken.query.filter_by(user_id=user.id).first()

def test_token_refresh(client):
    data = json.dumps({'username': 'test_user'})
    new_token = json.loads(create_token(client, data).data)
    assert new_token['access_token']
    assert new_token['refresh_token']
    assert new_token['expiry']
    header = {'Authorization': 'Bearer {}'.format(new_token['refresh_token'])}
    refresh_token_res = client.put('refresh_token', headers=header)
    assert refresh_token_res.status_code == 200
    refresh_token = json.loads(refresh_token_res.data)
    assert refresh_token['access_token'] 
    assert refresh_token['refresh_token']
    assert refresh_token['expiry']
    assert refresh_token['access_token'] != new_token['access_token'] 
    assert refresh_token['refresh_token'] != new_token['refresh_token']

def test_secret_endpoint(client):
    data = json.dumps({'username': 'test_user'})
    new_token = json.loads(create_token(client, data).data)
    header = {'Authorization': 'Bearer {}'.format(new_token['access_token'])}

    # without preserving original context
    secret_res = client.get('/secret', headers=header)
    assert not current_stateless_user # Ensure that it's not accessible outside of local request context
    secret_res = client.get('/secret', headers=header)
    assert secret_res.status_code == 200
    json_res = json.loads(secret_res.data)
    assert json_res['secret'] == 'Stateless auth is awesome :O'
    assert current_stateless_user._get_current_object() is None

    # while preserving original context
    with app.test_client() as c:
        secret_res = c.get('/secret', headers=header)
        assert secret_res.status_code == 200
        json_res = json.loads(secret_res.data)
        assert json_res['secret'] == 'Stateless auth is awesome :O'
        assert current_stateless_user.username == 'test_user'
        assert current_stateless_user._get_current_object().username == 'test_user'
        assert _get_stateless_user().username == 'test_user'

    #with app.app_context():
        #assert app.template_context_processors['current_stateless_user']
        #assert g.current_stateless_user.id ==1
        #assert current_app._get_current_object().current_stateless_user.id ==1
    #with app.test_request_context('/secret', headers=header): #New context not the app's
        #pass

def test_whoami(client):
    ''' server-side current_stateless_user inspection '''
    data = json.dumps({'username': 'test_user'})
    new_token = json.loads(create_token(client, data).data)
    header = {'Authorization': 'Bearer {}'.format(new_token['access_token'])}
    whoami_res = client.get('/whoami', headers=header)   
    assert whoami_res.status_code == 200
    json_res = json.loads(whoami_res.data)
    assert json_res['my_username'] == 'test_user' 

def test_request_context_is_flushed(client):
    res = client.get('no_current_stateless_user')
    assert res.status_code == 200
    res_json = json.loads(res.data)
    assert res_json['current_stateless_username'] == 'None'
    with app.test_client() as c:
        secret_res = c.get('/no_current_stateless_user')
        assert secret_res.status_code == 200
        json_res = json.loads(secret_res.data)
        assert json_res['current_stateless_username'] == 'None'
        assert current_stateless_user._get_current_object() is None

