from setuptools import setup, find_packages

setup(
    name="aws-ai-data-migrator",
    version="0.1.0",
    description="LLM-powered CLI for migrating unstructured data to AWS S3 and DynamoDB",
    author="Data Migration Team",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "anthropic==0.34.0",
        "boto3==1.34.0",
        "click==8.1.7",
        "pymongo==4.6.0",
        "rich==13.7.0",
        "python-dotenv==1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "aws-migrate=src.cli:main",
        ],
    },
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "pytest-cov==4.1.0",
            "moto==4.2.9",
        ],
    },
)
