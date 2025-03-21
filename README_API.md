# Whisper 字幕生成 API

这是一个基于OpenAI Whisper的异步字幕生成API，可以从音频或视频URL生成带时间轴的字幕。

## 特性

- 支持各种音频和视频格式
- 异步任务处理
- Redis任务状态同步
- 支持SRT和VTT字幕格式
- 支持语言指定（如中文）
- 自动硬件加速（MPS/CUDA）
- RESTful API接口
- 任务进度跟踪
- 字幕下载
- 视频音频提取

## 安装

1. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

2. 安装Redis
   ```bash
   # 使用Docker（推荐）
   docker run -d -p 6379:6379 --name redis redis:alpine
   
   # 或者使用你熟悉的方式安装Redis
   ```

3. 安装FFmpeg
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt update && sudo apt install ffmpeg`
   - Windows: 下载FFmpeg并添加到系统路径

## 配置

配置选项在`config.py`文件中，可以通过环境变量覆盖：

- `REDIS_HOST`: Redis主机地址（默认：localhost）
- `REDIS_PORT`: Redis端口（默认：6379）
- `REDIS_DB`: Redis数据库编号（默认：0）
- `API_HOST`: API服务监听地址（默认：0.0.0.0）
- `API_PORT`: API服务端口（默认：8000）
- `UPLOAD_FOLDER`: 上传文件存储目录（默认：uploads）
- `RESULT_FOLDER`: 结果文件存储目录（默认：results）

## 启动服务

使用以下命令启动服务：

```bash
# 方法1：使用提供的启动脚本
chmod +x start.sh
./start.sh

# 方法2：分别启动服务
# 终端1: 启动Celery Worker
celery -A worker.app worker --loglevel=info --concurrency=1

# 终端2: 启动API服务
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问 http://localhost:8000/docs 查看API文档。

## API使用

### 提交字幕生成任务

```bash
curl -X 'POST' \
  'http://localhost:8000/api/subtitle' \
  -H 'Content-Type: application/json' \
  -d '{
  "media_url": "https://example.com/audio.mp3",
  "model": "base",
  "language": "zh",
  "format": "srt"
}'
```

### 查询任务状态

```bash
curl -X 'GET' 'http://localhost:8000/api/subtitle/任务ID'
```

### 下载生成的字幕

```bash
curl -X 'GET' 'http://localhost:8000/api/subtitle/任务ID/download' -o subtitle.srt
```

### 从视频URL提取音频

```bash
curl -X 'POST' \
  'http://localhost:8000/api/extract-audio' \
  -H 'Content-Type: application/json' \
  -d '{
  "video_url": "https://example.com/video.mp4",
  "audio_format": "mp3"
}'
```

### 上传视频并提取音频

使用表单提交视频文件：

```bash
curl -X 'POST' \
  'http://localhost:8000/api/upload/extract-audio' \
  -F 'file=@/path/to/local/video.mp4' \
  -F 'audio_format=mp3'
```

### 列出所有任务

```bash
curl -X 'GET' 'http://localhost:8000/api/tasks'
```

### 删除任务

```bash
curl -X 'DELETE' 'http://localhost:8000/api/subtitle/任务ID'
```

## API参数

### 字幕生成API

提交任务时可以指定以下参数：

- `media_url`: 音频或视频的URL地址（必填）
- `model`: Whisper模型大小，可选值：tiny, base, small, medium, large（默认：base）
- `language`: 语言代码，如'zh'表示中文，不填则自动检测
- `format`: 字幕格式，可选值：srt, vtt（默认：srt）
- `max_line_length`: 每行字幕的最大字符数（默认：无限制）
- `cpu`: 是否强制使用CPU（默认：false）
- `no_mps`: 是否禁用MPS加速（默认：false）

### 音频提取API

从URL提取音频时可以指定以下参数：

- `video_url`: 视频的URL地址（必填）
- `audio_format`: 音频格式，可选值：mp3, wav, ogg, flac, m4a（默认：mp3）

上传视频提取音频时可以指定以下参数：

- `file`: 上传的视频文件（必填）
- `audio_format`: 音频格式，可选值：mp3, wav, ogg, flac, m4a（默认：mp3）

## 开发

- `app.py`: FastAPI主应用
- `worker.py`: Celery任务
- `config.py`: 配置文件
- `subtitle_generator.py`: 字幕生成核心功能

## 注意事项

- 较大的模型（medium, large）提供更高的准确性，但需要更多的计算资源和处理时间
- 首次运行时，程序会下载指定的模型文件
- 确保Redis服务正常运行，否则任务队列和状态同步将无法工作
- 音频提取需要FFmpeg正确安装在系统中
- 支持的视频格式：mp4, avi, mov, mkv, webm, flv, wmv
- 支持的音频格式：mp3, wav, ogg, flac, m4a 