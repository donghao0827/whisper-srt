import os
import json
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import redis
import uuid

import config
from worker import generate_subtitle_task, TASK_STATUS, download_media
from subtitle_generator import extract_audio

# 创建FastAPI应用
app = FastAPI(
    title="字幕生成API",
    description="基于Whisper的音频/视频字幕生成API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置静态文件服务
app.mount("/results", StaticFiles(directory=config.RESULT_FOLDER), name="results")
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_FOLDER), name="uploads")

# 连接Redis
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=int(config.REDIS_PORT),
    db=int(config.REDIS_DB),
    decode_responses=True
)

# 请求模型
class SubtitleRequest(BaseModel):
    media_url: HttpUrl
    model: Optional[str] = "base"
    language: Optional[str] = None
    format: Optional[str] = "srt"
    max_line_length: Optional[int] = None
    cpu: Optional[bool] = False
    no_mps: Optional[bool] = False

# 音频提取请求模型
class AudioExtractionRequest(BaseModel):
    video_url: HttpUrl
    audio_format: Optional[str] = "mp3"

# 状态响应模型
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Welcome to Whisper Subtitle API"}

@app.post("/api/extract-audio", response_model=Dict[str, str])
async def extract_audio_from_video_url(request: AudioExtractionRequest):
    """
    从视频URL提取音频文件
    
    - **video_url**: 视频URL
    - **audio_format**: 输出音频格式 (默认: mp3)
    """
    task_id = str(uuid.uuid4())
    
    try:
        # 下载视频文件
        video_path = download_media(str(request.video_url), task_id)
        
        # 检查是否为视频文件
        video_ext = video_path.split('.')[-1].lower()
        video_extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']
        
        if video_ext not in video_extensions:
            raise HTTPException(status_code=400, detail="提供的URL不是视频文件")
        
        # 提取音频
        audio_path = extract_audio(video_path, 
                                   output_audio=os.path.join(config.RESULT_FOLDER, f"{task_id}.{request.audio_format}"))
        
        # 获取音频URL
        audio_url = f"/results/{os.path.basename(audio_path)}"
        
        return {
            "task_id": task_id,
            "audio_url": audio_url,
            "filename": os.path.basename(audio_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音频提取失败: {str(e)}")

@app.post("/api/upload/extract-audio")
async def extract_audio_from_uploaded_video(
    file: UploadFile = File(...),
    audio_format: str = Form("mp3")
):
    """
    从上传的视频文件提取音频
    
    - **file**: 上传的视频文件
    - **audio_format**: 输出音频格式 (默认: mp3)
    """
    # 检查文件类型
    video_extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']
    file_ext = file.filename.split('.')[-1].lower()
    
    if file_ext not in video_extensions:
        raise HTTPException(status_code=400, detail="上传的文件不是支持的视频格式")
    
    task_id = str(uuid.uuid4())
    video_path = os.path.join(config.UPLOAD_FOLDER, f"{task_id}.{file_ext}")
    
    try:
        # 保存上传的视频文件
        with open(video_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # 提取音频
        audio_path = extract_audio(video_path, 
                                  output_audio=os.path.join(config.RESULT_FOLDER, f"{task_id}.{audio_format}"))
        
        # 获取音频URL
        audio_url = f"/results/{os.path.basename(audio_path)}"
        
        return {
            "task_id": task_id,
            "audio_url": audio_url,
            "filename": os.path.basename(audio_path)
        }
    except Exception as e:
        # 清理文件
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"音频提取失败: {str(e)}")

@app.post("/api/subtitle", response_model=Dict[str, str])
async def create_subtitle_task(request: SubtitleRequest):
    """
    提交音频/视频URL，异步生成字幕
    
    - **media_url**: 音频或视频的URL地址
    - **model**: Whisper模型大小 (tiny, base, small, medium, large)
    - **language**: 语言代码，如'zh'表示中文，不填则自动检测
    - **format**: 字幕格式 (srt 或 vtt)
    - **max_line_length**: 每行字幕的最大字符数
    - **cpu**: 是否强制使用CPU
    - **no_mps**: 是否禁用MPS加速
    """
    # 创建任务选项
    options = {
        'model': request.model,
        'language': request.language,
        'format': request.format,
        'max_line_length': request.max_line_length,
        'cpu': request.cpu,
        'no_mps': request.no_mps
    }
    
    # 提交Celery任务
    task = generate_subtitle_task.delay(str(request.media_url), options)
    
    return {"task_id": task.id}

@app.get("/api/subtitle/{task_id}", response_model=TaskStatusResponse)
async def get_subtitle_task(task_id: str):
    """
    获取字幕生成任务的状态
    
    - **task_id**: 任务ID
    """
    # 查询Celery任务状态
    task = generate_subtitle_task.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": "",
        "progress": 0
    }
    
    if task.state == 'PENDING':
        response["status"] = TASK_STATUS['PENDING']
        
    elif task.state == 'FAILURE':
        response["status"] = TASK_STATUS['FAILURE']
        response["error"] = str(task.info.get('error', 'Unknown error'))
        
    elif task.state in ['STARTED', 'DOWNLOADING', 'EXTRACTING', 'TRANSCRIBING']:
        response["status"] = TASK_STATUS.get(task.state, task.state)
        response["progress"] = task.info.get('progress', 0)
        
    elif task.state == 'SUCCESS':
        response["status"] = TASK_STATUS['SUCCESS']
        response["progress"] = 100
        
        # 获取结果
        if task.info:
            response["result"] = task.info
    
    return response

@app.get("/api/subtitle/{task_id}/download")
async def download_subtitle(task_id: str):
    """
    下载生成的字幕文件
    
    - **task_id**: 任务ID
    """
    # 检查任务状态
    task = generate_subtitle_task.AsyncResult(task_id)
    
    if task.state != 'SUCCESS':
        raise HTTPException(status_code=404, detail="任务未完成或不存在")
    
    # 获取任务结果
    if task.info and 'subtitle_file' in task.info:
        subtitle_file = os.path.join(config.RESULT_FOLDER, task.info['subtitle_file'])
        
        if os.path.exists(subtitle_file):
            return FileResponse(subtitle_file, filename=task.info['subtitle_file'])
    
    raise HTTPException(status_code=404, detail="字幕文件不存在")

@app.get("/api/tasks", response_model=List[Dict[str, Any]])
async def list_tasks():
    """
    列出所有任务
    """
    # 获取所有JSON结果文件
    results = []
    for filename in os.listdir(config.RESULT_FOLDER):
        if filename.endswith('.json'):
            file_path = os.path.join(config.RESULT_FOLDER, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                    results.append({
                        'task_id': task_data.get('task_id'),
                        'status': task_data.get('status'),
                        'media_url': task_data.get('media_url'),
                        'subtitle_file': task_data.get('subtitle_file'),
                        'created_at': os.path.getctime(file_path)
                    })
            except:
                pass
    
    # 按创建时间排序
    results.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    
    return results

@app.delete("/api/subtitle/{task_id}")
async def delete_subtitle_task(task_id: str):
    """
    删除字幕生成任务及相关文件
    
    - **task_id**: 任务ID
    """
    json_file = os.path.join(config.RESULT_FOLDER, f"{task_id}.json")
    srt_file = os.path.join(config.RESULT_FOLDER, f"{task_id}.srt")
    vtt_file = os.path.join(config.RESULT_FOLDER, f"{task_id}.vtt")
    
    deleted = False
    
    # 删除JSON结果
    if os.path.exists(json_file):
        os.remove(json_file)
        deleted = True
    
    # 删除SRT文件
    if os.path.exists(srt_file):
        os.remove(srt_file)
        deleted = True
    
    # 删除VTT文件
    if os.path.exists(vtt_file):
        os.remove(vtt_file)
        deleted = True
    
    # 删除可能的上传文件
    for ext in config.ALLOWED_EXTENSIONS:
        upload_file = os.path.join(config.UPLOAD_FOLDER, f"{task_id}.{ext}")
        if os.path.exists(upload_file):
            os.remove(upload_file)
            deleted = True
    
    if deleted:
        return {"message": "Task deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Task not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT) 