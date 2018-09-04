from functools import wraps

from werkzeug.local import LocalProxy
from werkzeug.security import safe_str_cmp
from flask import jsonify, request, current_app, _request_ctx_stack, has_request_context
from flask.signals import Namespace

__title__ = 'Flask-Stateless-Auth'
__description__ = 'Stateless user authentication management with regular tokens'
__url__ = 'https://github.com/omarryhan/flask-stateless-auth'
__version_info__ = ('0', '0', '1')
__version__ = '.'.join(__version_info__)
__author__ = 'Omar Ryhan'
__author_email__ = 'omarryhan@gmail.com'
__maintainer__ = 'Omar Ryhan'
__license__ = 'MIT'
__copyright__ = '(c) 2018 by Omar Ryhan'
__all__ = [] 

# TODO: Write some unit tests
# TODO: Test app_context_processor
# TODO: Test different auth headers and types
# TODO: Test invalid tokens
# TODO: Test invalid token_types
# TODO: Make the "create token" endpoint to first check if a user owns a token, if true, refresh, if not, create to remove the one-to-one violation warning

AUTH_TYPE = 'Bearer'
AUTH_HEADER = 'Authorization'
ADD_CONTEXT_PROCESSOR = True

_signals = Namespace()

user_authenticated = _signals.signal('user-authenticated')
user_unauthorized = _signals.signal('user-unauthorized')


current_stateless_user = LocalProxy(lambda: _get_stateless_user())

def _get_stateless_user():
    return getattr(_request_ctx_stack.top, 'stateless_user', None)

def token_required(token_type, auth_type=AUTH_TYPE):
    '''
    Unlike flask_login's 'login_required', this both authenticates and enforces user authentication
    TODO: Find a workaround to change the default for auth_type to 
    TODO: `current_app._get_current_object().stateless_auth_manager.self.auth_type` ie. `app.stateless_auth_manager.self.auth_type`
    TODO: instead of hardcoding it to the module's global vars.
    TODO: The reason you can't set it is because there is no app context and therefore no stateless_auth_manager
    TODO: at the time the interpreter parses the token_required decorator
    '''
    def inner(f):
        @wraps(f)
        def innermost(*args, **kwargs):
            try:
                current_app._get_current_object().stateless_auth_manager._set_user(token_type, auth_type)
            except StatelessAuthError as e:
                user_unauthorized.send(current_app.stateless_auth_manager)
                raise e
            except AttributeError as e:
                print('Provide a token callback, a user callback and a StatelessAuthError handler as shown in StatelessAuthManager\'s docs')
                raise e
            else:
                user_authenticated.send(current_app.stateless_auth_manager)
                return f(*args, **kwargs)
        return innermost
    return inner

class StatelessAuthError(Exception, object):
    ''' 400 Bad request, 401 Unauthorized, 402 Payment required, 403 Forbidden '''
    ''' Error types: 1) Token 2) Subscription 3) User '''
    def __init__(self, msg, code, type_):
        self.code = code
        self.msg = msg
        self.type = type_
        self.full_msg = '{} error: {}'.format(type_, msg)
        super(StatelessAuthError, self).__init__(self.full_msg)

class StatelessAuthManager:
    '''
    '''
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.stateless_auth_manager = self
        self.auth_type = app.config.get('AUTH_TYPE', AUTH_TYPE)
        self.auth_header = app.config.get('AUTH_HEADER', AUTH_HEADER)
        self.add_context_processor = app.config.get('ADD_CONTEXT_PROCESSOR', ADD_CONTEXT_PROCESSOR)
        app.teardown_request(self.teardown)

    def teardown(self, exception):
        ''' TODO: Should there be anything here?'''
        pass

    def user_loader(self, callback):
        self._user_callback = callback
        return callback

    def token_loader(self, callback):
        self._token_callback = callback
        return callback

    def _load_user_model(self, user_id):
        return self._user_callback(user_id)

    def _load_token_model(self, token, token_type):
        return self._token_callback(token=token, token_type=token_type)

    def _load_token_from_request(self, auth_type):
        token = request.headers.get(self.auth_header)
        if token: token = token.split(" ")
        else: raise StatelessAuthError(msg="No token provided", code=400, type_='Token')
        if len(token) == 2:
            if safe_str_cmp(token[0], auth_type):
                return token[1]
            else: raise StatelessAuthError(msg="Invalid token type", code=400, type_='Token')
        else: raise StatelessAuthError(msg='Invalid number of arguments in token header', code=400, type_='Token')

    def _set_user(self, token_type, auth_type):
        token = self._load_token_from_request(auth_type)
        token_model = self._load_token_model(token=token, token_type=token_type)
        self._check_token(token_model, token_type)
        user = self._load_user_model(token_model)
        self._check_user(user)
        self._update_request_context_with(user=user, token=token)
        if self.add_context_processor:
            self._update_context_processor_with(user)

    def _check_token(self, token_model, token_type):
        if token_model.token_expired(token_type):
            raise StatelessAuthError(msg='{} token expired'.format(token_type), code=401, type_='Token')

    def _check_user(self, user):
        if not user or not user.is_active:
            raise StatelessAuthError(msg='Invalid User', code=401, type_='User')

    def _update_context_processor_with(self, user):
        current_app._get_current_object().context_processor(dict(current_stateless_user=user))

    def _update_request_context_with(self, user=None, token=None):
        ctx = _request_ctx_stack.top
        if user is not None: ctx.stateless_user = user
        if token is not None: ctx.token = token
  
class TokenMixin:
    def token_expired(self, token_type):
        return False

class UserMixin:
    @property
    def is_active(self):
        return True


