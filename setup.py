from setuptools import setup, find_packages

setup(
    name="Tech Sentry",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "schedule",
        "pyyaml"
    ],
    entry_points={
        "console_scripts": [
            "github-argus=scripts.run:run",
        ],
    },
)
