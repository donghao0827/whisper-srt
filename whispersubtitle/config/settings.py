"""
应用配置
"""

import os
from pathlib import Path

# 基础路径设置
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "results")
VIDEOS_FOLDER = os.environ.get("VIDEOS_FOLDER", os.path.join(BASE_DIR, "videos"))

# 创建必要的目录
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(VIDEOS_FOLDER, exist_ok=True)

# Redis配置
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_DB = os.environ.get("REDIS_DB", "0")

# Celery配置
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# 允许的扩展名
ALLOWED_EXTENSIONS = [
    'mp3', 'wav', 'ogg', 'flac', 'm4a',  # 音频格式
    'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'  # 视频格式
]

# OBS存储配置
USE_OBS_STORAGE = os.environ.get("USE_OBS_STORAGE", "False").lower() == "true"
OBS_ENDPOINT = os.environ.get("OBS_ENDPOINT", "")
OBS_ACCESS_KEY = os.environ.get("OBS_ACCESS_KEY", "")
OBS_SECRET_KEY = os.environ.get("OBS_SECRET_KEY", "")
OBS_SUBTITLES_BUCKET = os.environ.get("OBS_SUBTITLES_BUCKET", "srts")
OBS_REGION = os.environ.get("OBS_REGION", "") 