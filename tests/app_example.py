import os
import datetime
import secrets
import json

from flask import Flask, abort, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from werkzeug.security import safe_str_cmp

from flask_stateless_auth import StatelessAuthError, StatelessAuthManager, current_stateless_user, UserMixin, TokenMixin, token_required

db = SQLAlchemy()
stateless_auth_manager = StatelessAuthManager()
app = Flask(__name__.split('.')[0])

class Config:
    # Stateless auth configs
    #DEFAULT_AUTH_TYPE = 'Bearer'         # Default
    #TOKEN_HEADER = 'Authorization'# Default
    #ADD_CONTEXT_PROCESSOR = True  # Default
    # Other configs
    TESTING = False
    TOKENS_BYTES_LENGTH = 32
    ACCESS_TOKEN_DEFAULT_EXPIRY = 3600 # seconds
    REFRESH_TOKEN_DEFAULT_EXPIRY = 365 # days
    DB_NAME = 'flask_stateless_auth_db'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DB_NAME
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, unique=True)
    api_token = db.relationship('ApiToken', backref='user', uselist=False)


class ApiToken(db.Model, TokenMixin):
    __tablename__ = 'api_token'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    refresh_token = db.Column(db.String, nullable=False, unique=True, index=True)
    access_token = db.Column(db.String, nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    refresh_token_expiry = db.Column(db.Integer, nullable=False, default=Config.REFRESH_TOKEN_DEFAULT_EXPIRY)
    access_token_expiry = db.Column(db.Integer, nullable=False, default=Config.ACCESS_TOKEN_DEFAULT_EXPIRY)

    def __init__(self, user_id, refresh_token_expiry=None, access_token_expiry=None, tokens_bytes_length=Config.TOKENS_BYTES_LENGTH):
        self.user_id = user_id
        if refresh_token_expiry and type(refresh_token_expiry) == int:
            self.refresh_token_expiry = refresh_token_expiry
        if access_token_expiry and type(access_token_expiry) == int:
            self.access_token_expiry = access_token_expiry
        #create tokens
        self.refresh_tokens(tokens_bytes_length)

    def refresh_tokens(self, tokens_bytes_length=Config.TOKENS_BYTES_LENGTH):
        self.access_token = secrets.base64.standard_b64encode(secrets.token_bytes(tokens_bytes_length)).decode('utf-8')
        self.refresh_token = secrets.base64.standard_b64encode(secrets.token_bytes(tokens_bytes_length)).decode('utf-8')
        self.created_on = datetime.datetime.now()

    @property
    def access_is_expired(self):
        expiry_time = self.created_on + datetime.timedelta(seconds=self.access_token_expiry)
        if datetime.datetime.now() <= expiry_time:
            return False
        else:
            return True

    @property
    def refresh_is_expired(self):
        expiry_time = self.created_on + datetime.timedelta(days=self.refresh_token_expiry)
        if datetime.datetime.now() <= expiry_time:
            return False
        else:
            return True

    def token_expired(self, token_type, auth_type):
        if token_type == 'access':
            return self.access_is_expired
        elif token_type == 'refresh':
            return self.refresh_is_expired
        else:
            raise NameError('Invalid token name')
    
    @property
    def as_dict(self):
        return {
            'access_token': self.access_token,
            'expiry': self.access_token_expiry,
            'refresh_token': self.refresh_token
        }

@stateless_auth_manager.user_loader
def user_by_token(token):
    try:
        user = User.query.filter_by(id=token.user_id).one()
    except NoResultFound:
        raise StatelessAuthError(msg='Server error', code=500, type_='Server') # Tokens should always have a user, hence the 500 not the 
    except Exception as e:
        raise StatelessAuthError(msg='Server error', code=500, type_='Server')
        #log.critical(e)
    else:
        return user

@stateless_auth_manager.token_loader
def token_model_by(token, auth_type, token_type='access'):
    try:
        if token_type=='access':
            token_model = ApiToken.query.filter_by(access_token=token).one()
        elif token_type=='refresh':
            token_model = ApiToken.query.filter_by(refresh_token=token).one()
    except NoResultFound:
        raise StatelessAuthError(msg='{} token doesn\'t belong to a user'.format(token_type), code=401, type_='Token')
    except Exception as e:
        raise StatelessAuthError(msg='Server error', code=500, type_='Server')
        #log.critical(e)
    else:
        return token_model

@app.route('/')
def index():
    return 'hello', 200

@app.route('/user', methods=['GET', 'POST', 'PUT', 'DELETE'])
def user_endpoint():
    data = json.loads(request.data)
    if request.method == 'POST':
        user = User(username=data['username'])
        db.session.add(user)
    elif request.method == 'DELETE':
        user = User.query.filter_by(username=data['username']).first()
        db.session.delete(user)
    db.session.commit()
    data = {'msg': 'Success!'}
    return jsonify(data), 201

@app.route('/create_token', methods=['POST'])
def create_token():
    data = json.loads(request.data)
    user = User.query.filter_by(username=data['username']).first()
    if user.api_token:
        token = user.api_token
        token.refresh_tokens()
    else:
        token = ApiToken(user_id=user.id)
    db.session.add(token)
    db.session.commit()
    return jsonify(token.as_dict), 201

@app.route('/delete_token', methods=['DELETE'])
def delete_token():
    data = json.loads(request.data)
    token = User.query.filter_by(username=data['username']).one().api_token
    db.session.delete(token)
    db.session.commit()
    return jsonify({'msg': 'Success!'}), 201

@app.route('/refresh_token', methods=['PUT'])
@token_required(token_type='refresh')
def refresh_token():
    current_stateless_user.api_token.refresh_tokens()
    db.session.add(current_stateless_user.api_token)
    db.session.commit()
    return jsonify(current_stateless_user.api_token.as_dict), 201

@app.route('/secret', methods=['GET'])
@token_required(token_type='access') #access by default
def secret():
    data = {'secret': 'Stateless auth is awesome :O'}
    return jsonify(data), 200

@app.route('/whoami', methods=['GET'])
@token_required()
def whoami():
    data = {'my_username': current_stateless_user.username}
    return jsonify(data), 200

@app.route('/no_current_stateless_user')
def no_current_stateless_user():
    if not current_stateless_user:
        username = 'None'
    else: username = current_stateless_user.username
    data = {'current_stateless_username': username}
    return jsonify(data), 200

@app.errorhandler(StatelessAuthError)
def handle_stateless_auth_error(error):
    return jsonify({'error': error.full_msg}), error.code

if __name__ == '__main__':
    app.config.from_object(Config())
    db.init_app(app)
    with app.app_context():
        db.create_all()
    stateless_auth_manager.init_app(app)
    app.run()
