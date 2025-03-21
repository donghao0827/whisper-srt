#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="whispersubtitle",
    version="1.0.0",
    author="WhisperSubtitle Team",
    author_email="example@example.com",
    description="基于OpenAI Whisper的多功能字幕生成工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/whispersubtitle",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "openai-whisper>=20231117",
        "torch>=2.0.0",
        "fastapi>=0.95.0",
        "uvicorn>=0.22.0",
        "celery>=5.3.0",
        "redis>=4.5.0",
        "requests>=2.28.0",
        "python-multipart>=0.0.6",
        "boto3>=1.28.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "whispersubtitle=whispersubtitle.main:main",
        ],
    },
) 