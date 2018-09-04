# Flask-Stateless-Auth

A very lightweight db-stored-token authentication library



## Features:

- Flask-Stateless-Auth assists with stateless authentication in case a Flask developer decides to:
    - Authenticate statelessly without the use of sessions. (Typically used when implementing REST APIs).
    - Not to issue signed tokens e.g.(JWT), instead issue tokens that are to be validated against a db or a datastore of sorts.
    - 
- Flask-Stateless-Auth does not enforce the usage of any kind of db or data structure
- 
- Flask-Stateless-Auth however enforces the use of a certian format for your chosen authorization header, the format is as follows:
    - {'header_name': 'auth_type' + ' ' + 'token'}
    - 
- Developer is free to implement their own authorization protocol.
    - A typical `header_name` is 'Authorization'
    - A typical `auth_type` is 'Bearer'
    - A typical `token` is a random string.
    - A typical `token_type` is: an access, refresh or permenant token
- Flask-Stateless-Auth stores a current_stateless_user variable in the request context upon authentication using the `token_required` decorator

## Important Remarks:

Flask-Stateless-Auth needs 2 callbacks in order to function properly:

- `token_loader`: should load a token given, a token and a token_type
- `user_loader`: Should load a user given a token(token loaded from token loader)

Flask-Stateless-Auth also needs a StatlessAuthError error handler. The handler will receive an error with the following attributes:

- `error.code`: suggested status code
- `error.msg`: message
- `error.type`: Error type ('Token', 'User')
- The developer can then decide how to handle each error seperately controlling the info they would want to give out to the api client.

Last but not least, the developer should raise a StatelessAuthError in the `token_loader` and `user_loader` callbacks in case any error occurs that might cause the function to return None.

## API

- StatelessAuthManager
- StatelessAuthError
- current_stateless_user
- token_required()
- TokenMixin
- UserMixin

## Quick Start 

    # initializations
    stateless_auth_manager = StatelessAuthManager()
    app = Flask(__name__.split('.')[0])
    
    # configs
    class Config:
        #TOKEN_TYPE = 'Bearer'         # Default
        #TOKEN_HEADER = 'Authorization'# Default
        #ADD_CONTEXT_PROCESSOR = True  # Default
    
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
    @stateless_auth_manager.user_loader
    def user_by_token(token):
        try:
            for user in users:
                if user.id == token.id: return user # Use flask.str_safecmp instead
                    raise StatelessAuthError(msg='token belongs to a user but user wasn't found, code=401, type_='User')
        except:
            raise StatelessAuthError(msg='internal server error', code=500, type_='Token')
    
    # Second loader
    @stateless_auth_manager.token_loader
    def token_by(token, token_type):
        try:
            for token in tokens:
                if token_type == 'access'
                    if token.access_token == token:
                        return token
                elif token_type == 'refresh':
                    if token.refresh_token == token:
                        return token
            raise StatelessAuthError(msg='{} token doesn\'t belong to a user'.format(token.type), code=401, type_='Token')
        except:
            raise StatelessAuthError(msg='internal server error', code=500, type_='Token')
    
    # Error handler
    @app.errorhandler(StatelessAuthError)
    def handle_stateless_auth_error(error):
        return jsonify({'error': error.msg}), error.code
    
    @app.route('/secret', methods=['GET'])
    @token_required(token_type='access', auth_type='Bearer') #access by default
    def secret():
        data = {'secret': 'Stateless auth is awesome :O'}
        return jsonify(data), 200
    
    @app.route('/whoami', methods=['GET'])
    @token_required('access')
    def whoami():
        data = {'my_username': current_stateless_user.username}
        return jsonify(data), 200
    
    if __name__ == '__main__':
        app.config.from_object(Config())
        stateless_auth_manager.init_app(app)
        app.run()

- For a comprehensive view of how an app should look like, check out: `app_example.py` and the tests if you feel like it.

## Testing
run tests with: `pytest flask-stateless-auth/test_app.py`
