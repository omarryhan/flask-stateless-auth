# Flask-Stateless-Auth

A lightweight no-batteries-included stateless authentication extension for Flask.


## Features:

- Flask-Stateless-Auth assists with stateless authentication in case a Flask developer decides to:
    - Authenticate statelessly without the use of sessions. (Typically used when implementing REST APIs).
    - Not to issue signed tokens e.g.(JWT), instead issue tokens that are to be validated against a db or a datastore of sorts.

- Flask-Stateless-Auth is similar to OAUTH2 but it's specifically designed to provide **1st party** clients the ability to authenticate with **secret** bearer tokens.
- Flask-Stateless-Auth stores a current_stateless_user variable in the request context upon authentication using the `token_required` decorator

- Developer is free to implement their own authorization scheme, However:
    - A typical `header_name` is 'Authorization'
    - A typical `auth_type` is 'Bearer'
    - A typical `token` is a random b64 encoded string.
    - A typical `token_type` is: an access or refresh token

## Important Remarks:

1. Flask-Stateless-Auth however enforces the use of a certian format for your chosen authorization header, the format is as follows:
    - {'header_name': 'auth_type' + ' ' + 'token'}

2. Flask-Stateless-Auth needs 2 callbacks in order to function properly:

    1. `token_loader`: Should load a token from your models given, a `token`, `token_type`, and `auth_type`
    2. `user_loader`: Should load a user from your models given token(token loaded from token loader)

3. Flask-Stateless-Auth also needs a StatlessAuthError error handler. The handler will receive an error with the following attributes:

    - `error.code`: suggested status code
    - `error.msg`: message
    - `error.type`: Error type ('token', 'request', 'scope')
    - `error.full_msg`: Error msg + type
    - The developer can then decide how to handle each error seperately by controlling the info they would want to give out to the api client.

4. It is recommended that you raise a StatelessAuthError in case a token or a user cannot be loaded. Provide reasonably descriptive information for the client on the why the user couldn't be loaded . However, you can still return None and FlaskStatelessAuth will return a generic error message and code.

5. Your user model must have a `is_active` property which returns a boolean.

6. Yout token model must have a `is_expired()` method that takes a request's `auth_type` (e.g. 'bearer') and `token_type` (e.g. 'access' or 'refresh').

7. If you don't want to implement point `5.` and `6.` then you can simply make you user and token model inherit from the `UserMixin` and `TokenMixin` mixins respecitvely.

## API

- StatelessAuthManager
- StatelessAuthError
- current_stateless_user
- token_required()
- TokenMixin
- UserMixin

## Installation

`$pip install flask-stateless-auth`

## Quick Start 

    # initializations
    stateless_auth_manager = StatelessAuthManager()
    app = Flask(__name__.split('.')[0])
    
    # configs
    class Config:
        #TOKEN_TYPE = 'Bearer'         # Default
        #TOKEN_HEADER = 'Authorization'# Default
        #ADD_CONTEXT_PROCESSOR = True  # Default
        #DEFAULT_TOKEN_TYPE = 'access' # Default

    # models
    class User(UserMixin):
        def __init__(self, id, username):
            self.id = id
            self.username = username
    
    class Token(TokenMixin):
        def __init__(self, user_id, access_token, refresh_token):
            self.user_id = user_id
            self.access_token = access_token
            self.refresh_token = refresh_token 
    
    # db
    users = [
        User(1, 'first_user'),
        User(2, 'second_user')
    ]
    
    tokens = [
        Token(1, 'first_user_access_token', 'first_user_refresh_token'),
        Token(2, 'second_user_access_token', 'second_user_refresh_token')
    ]

    # First loader
    @stateless_auth_manager.token_loader
    def token_by(token, token_type, auth_type):
    ''' where `token` is the token loaded from the header '''
        try:
            for token in tokens:
                if token_type == 'access'
                    if token.access_token == token:
                        return token
                elif token_type == 'refresh':
                    if token.refresh_token == token:
                        return token
            raise StatelessAuthError(msg='{} Invalid token'.format(token.type), code=401, type_='Token')
        except Exception as e:
            log.critical(e)
            raise StatelessAuthError(msg='internal server error', code=500, type_='Server')
    
    # Second loader
    @stateless_auth_manager.user_loader
    def user_by_token(token):
    ''' where `token` is the token model loaded from the token table '''
        try:
            for user in users:
                if user.id == token.id: return user
        except Exception as e:
            log.critical(e)
            raise StatelessAuthError(msg='internal server error', code=500, type_='Server')
        log.critical('token: {} belongs to a user: {} but user wasn't found'.format(token.id, user.id))
        raise StatelessAuthError(msg='internal server error', code=500, type_='Server')
    
    # Error handler
    @app.errorhandler(StatelessAuthError)
    def handle_stateless_auth_error(error):
        return jsonify({'error': error.full_msg}), error.code
    
    @app.route('/secret', methods=['GET'])
    @token_required(token_type='access', auth_type='Bearer') #access by default
    def secret():
        data = {'secret': 'Stateless auth is awesome :O'}
        return jsonify(data), 200
    
    @app.route('/whoami', methods=['GET'])
    @token_required()
    def whoami():
        data = {'my_username': current_stateless_user.username}
        return jsonify(data), 200
    
    if __name__ == '__main__':
        app.config.from_object(Config())
        stateless_auth_manager.init_app(app)
        app.run()

- For a more comprehensive illustration, check out: `tests/app_example.py` and `tests/test_app.py`.

## Testing
run tests with: `pytest -v`
