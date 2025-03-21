import os

# Redis配置
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Celery配置
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# API配置
API_HOST = os.environ.get('API_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('API_PORT', '8000'))

# 存储配置
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
RESULT_FOLDER = os.environ.get('RESULT_FOLDER', 'results')
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'mp4', 'avi', 'mov', 'mkv', 'webm'}

# 创建必要的文件夹
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True) 