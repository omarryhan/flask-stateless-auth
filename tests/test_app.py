import os
import json
import pytest
import pprint
import tempfile
import random
import string

from flask import request, current_app, g

from .app_example import db, app, stateless_auth_manager, User, ApiToken
from flask_stateless_auth import current_stateless_user, _get_stateless_user


class TestConfig():
    #DEFAULT_AUTH_TYPE = 'Bearer' # Default
    #AUTH_HEADER = 'Authorization'# Default
    #ADD_CONTEXT_PROCESSOR = True # Default
    #DEFAULT_TOKEN_TYPE = 'access'# Default
    ## Other configs ##
    TESTING = True
    TOKENS_BYTES_LENGTH = 32
    ACCESS_TOKEN_DEFAULT_EXPIRY = 3600 # seconds
    REFRESH_TOKEN_DEFAULT_EXPIRY = 365 # days
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_FILE_DESCRIPTOR, DB_NAME = tempfile.mkstemp(dir=BASE_DIR)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DB_NAME
    SQLALCHEMY_TRACK_MODIFICATIONS = False

def user_string_generator(length=10, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(length))

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

@pytest.fixture('session')
def valid_test_user(client):
    user = {'username': user_string_generator()}
    data = json.dumps(user)
    res = client.post('/user', data=data)
    assert res.status_code == 201
    yield user
    res = client.delete('/user', data=data)
    assert res.status_code == 201

@pytest.fixture('function')
def valid_test_user_token(client, valid_test_user):
    data = json.dumps(valid_test_user)
    res = client.post('/create_token', data=data)
    assert res.status_code == 201
    tokens = json.loads(res.data)
    yield tokens
    res = client.delete('/delete_token', data=data)
    assert res.status_code == 201

def test_current_stateless_user_is_none():
    assert not current_stateless_user # Shouldn't test it with `is None` as it's a LocalProxy type

def test_app_is_functional(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b'hello' in res.data

def test_user_created(client, valid_test_user):
    with app.app_context():
        assert User.query.filter_by(username=valid_test_user['username']).one()

def test_token_created(client, valid_test_user_token, valid_test_user):
    token = valid_test_user_token 
    assert token['access_token']
    assert token['refresh_token']
    assert token['expiry']
    with app.app_context():
        user = User.query.filter_by(username=valid_test_user['username']).one()
        assert ApiToken.query.filter_by(user_id=user.id).one()

def test_token_refresh(client, valid_test_user, valid_test_user_token):
    new_token = valid_test_user_token
    header = {'Authorization': 'Bearer {}'.format(new_token['refresh_token'])}
    refresh_token_res = client.put('refresh_token', headers=header)
    assert refresh_token_res.status_code == 201
    refresh_token = json.loads(refresh_token_res.data)
    assert refresh_token['access_token'] 
    assert refresh_token['refresh_token']
    assert refresh_token['expiry']
    assert refresh_token['access_token'] != new_token['access_token'] 
    assert refresh_token['refresh_token'] != new_token['refresh_token']

def test_secret_valid_call(client, valid_test_user, valid_test_user_token):
    auth_header = {'Authorization': 'Bearer {}'.format(valid_test_user_token['access_token'])}

    # without preserving original context
    secret_res = client.get('/secret', headers=auth_header)
    assert not current_stateless_user # Ensure that it's not accessible outside of local request context
    secret_res = client.get('/secret', headers=auth_header)
    assert secret_res.status_code == 200
    json_res = json.loads(secret_res.data)
    assert json_res['secret'] == 'Stateless auth is awesome :O'
    assert current_stateless_user._get_current_object() is None

    # while preserving original context
    with app.test_client() as c:
        secret_res = c.get('/secret', headers=auth_header)
        assert secret_res.status_code == 200
        json_res = json.loads(secret_res.data)
        assert json_res['secret'] == 'Stateless auth is awesome :O'
        assert current_stateless_user.username == valid_test_user['username']
        assert current_stateless_user._get_current_object().username == valid_test_user['username']
        assert _get_stateless_user().username == valid_test_user['username']

    #with app.app_context():
        #assert app.template_context_processors['current_stateless_user']
        #assert g.current_stateless_user.id ==1
        #assert current_app._get_current_object().current_stateless_user.id ==1
    #with app.test_request_context('/secret', headers=header): #New context not the app's
        #pass
def test_secret_endpoint_invalid_token(client, valid_test_user_token):
    bad_token = valid_test_user_token['access_token'] + 'bad_string'
    header = {'Authorization': 'Bearer {}'.format(bad_token)}

    secret_res = client.get('/secret', headers=header)
    assert secret_res.status_code == 401
    json_res = json.loads(secret_res.data)
    assert json_res.get('secret') is None

def test_secret_endpoint_bad_request(client, valid_test_user_token):
    bad_request = valid_test_user_token['access_token'] + 'bad string for a bad request)&)YHJhh98%)%&^*)&)@#$%تةنةنةتﻻ'
    header = {'Authorization': 'Bearer {}'.format(bad_request)}

    secret_res = client.get('/secret', headers=header)
    assert secret_res.status_code == 400
    json_res = json.loads(secret_res.data)
    assert json_res.get('secret') is None

def test_invalid_token_type(client, valid_test_user_token):
    header = {'Authorization': 'Snaker {}'.format(valid_test_user_token['access_token'])}

    secret_res = client.get('/secret', headers=header)
    assert secret_res.status_code == 400
    json_res = json.loads(secret_res.data)
    assert json_res.get('secret') is None

def test_invalid_auth_header(client, valid_test_user_token):
    header = {'NotAuthorization': 'Bearer {}'.format(valid_test_user_token['access_token'])}

    secret_res = client.get('/secret', headers=header)
    assert secret_res.status_code == 400
    json_res = json.loads(secret_res.data)
    assert json_res.get('secret') is None

def test_whoami(client, valid_test_user, valid_test_user_token):
    ''' server-side current_stateless_user inspection '''
    header = {'Authorization': 'Bearer {}'.format(valid_test_user_token['access_token'])}
    whoami_res = client.get('/whoami', headers=header)   
    assert whoami_res.status_code == 200
    json_res = json.loads(whoami_res.data)
    assert json_res['my_username'] == valid_test_user['username'] 

def test_request_context_is_flushed(client):
    res = client.get('/no_current_stateless_user')
    assert res.status_code == 200
    res_json = json.loads(res.data)
    assert res_json['current_stateless_username'] == 'None'
    with app.test_client() as c:
        secret_res = c.get('/no_current_stateless_user')
        assert secret_res.status_code == 200
        json_res = json.loads(secret_res.data)
        assert json_res['current_stateless_username'] == 'None'
        assert current_stateless_user._get_current_object() is None

