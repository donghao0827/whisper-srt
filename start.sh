#!/bin/bash

# 启动Redis（如果使用Docker）
# docker run -d -p 6379:6379 --name redis-whisper redis:alpine

# 在后台启动Celery worker
python -m celery -A whispersubtitle.api.worker.app worker --loglevel=info --concurrency=1 &

# 记录Celery的PID
CELERY_PID=$!

# 启动FastAPI应用
python -m uvicorn whispersubtitle.api.app:app --host 0.0.0.0 --port 8000 --reload

# 如果FastAPI退出，确保关闭Celery worker
kill $CELERY_PID 