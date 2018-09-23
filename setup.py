import setuptools

install_requires = [
    'flask'
]

tests_require = [
    'flask_sqlalchemy',
    'pytest',
    'tox'
]

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="flask-stateless-auth",
    version="0.0.15",
    author="Omar Ryhan",
    author_email="omarryhan@gmail.com",
    license="MIT",
    description="Flask stateless authentication with secrets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires,
    tests_require=tests_require,
    url="https://github.com/omarryhan/flask-stateless-auth",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
