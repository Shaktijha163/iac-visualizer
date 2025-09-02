from setuptools import setup, find_packages

setup(
    name="iac-visualizer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
        "fastapi>=0.104",
        "uvicorn>=0.24",
        "requests>=2.31",
        "networkx>=3.2",
        "python-multipart>=0.0.6",
        "aiofiles>=23.2",
        "jsonschema>=4.20",
    ],
    entry_points={
        'console_scripts': [
            'iacviz=cli.main:main',
        ],
    },
    python_requires='>=3.8',
)
