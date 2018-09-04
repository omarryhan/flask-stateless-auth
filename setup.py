from distutils.core import setup

install_requires = [
    'flask'
]

tests_require = [
    'flask_sqlalchemy' 
    'pytest'
]

setup(
    name='flask-stateless-auth',
    version='0.1dev',
    packages=['flask_stateless_auth',],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README').read(),
    install_requires=install_requires,
    tests_require=tests_require,
)
