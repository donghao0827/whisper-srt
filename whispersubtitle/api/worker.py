"""
异步字幕生成任务处理器
"""

import os
import uuid
import time
import json
import requests
import torch
from celery import Celery
from celery.utils.log import get_task_logger

from whispersubtitle.config import (
    CELERY_BROKER_URL, 
    CELERY_RESULT_BACKEND, 
    UPLOAD_FOLDER,
    RESULT_FOLDER,
    VIDEOS_FOLDER,
    ALLOWED_EXTENSIONS,
    USE_OBS_STORAGE
)
from whispersubtitle.core import extract_audio, generate_subtitles
from whispersubtitle.utils.obs_storage import obs_storage

# 创建Celery实例
app = Celery('subtitle_worker',
             broker=CELERY_BROKER_URL,
             backend=CELERY_RESULT_BACKEND)

# 配置Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
)

# 获取任务日志记录器
logger = get_task_logger(__name__)

# 任务状态
TASK_STATUS = {
    'PENDING': '等待处理',
    'STARTED': '处理中',
    'DOWNLOADING': '下载中',
    'EXTRACTING': '提取音频中',
    'TRANSCRIBING': '生成字幕中',
    'SUCCESS': '处理完成',
    'FAILURE': '处理失败',
    'RETRY': '重试中',
    'REVOKED': '任务取消'
}

def download_media(url, task_id):
    """从URL下载媒体文件"""
    logger.info(f"开始下载文件: {url}")
    
    # 创建文件名
    ext = url.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = 'mp4'  # 默认扩展名
    
    filename = f"{task_id}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # 下载文件
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"文件下载完成: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        raise

@app.task(bind=True, name='generate_subtitle')
def generate_subtitle_task(self, media_url=None, options=None):
    """异步生成字幕的Celery任务"""
    task_id = self.request.id
    if options is None:
        options = {}
    
    # 默认选项
    default_options = {
        'model': 'base',
        'language': None,
        'format': 'srt',
        'max_line_length': None,
        'cpu': False,
        'no_mps': False
    }
    
    # 合并默认选项和用户选项
    default_options.update(options)
    options = default_options
    
    # 更新任务状态
    self.update_state(state='STARTED', meta={
        'status': TASK_STATUS['STARTED'],
        'progress': 0
    })
    
    try:
        # 处理媒体文件
        media_key = options.get('media_key')
        
        if media_key:
            # 使用media_key从本地目录查找视频
            logger.info(f"使用media_key: {media_key}查找本地视频文件")
            
            # 在uploads目录和视频目录查找文件
            local_paths = [
                os.path.join(UPLOAD_FOLDER, media_key),  # 完整路径
                os.path.join(UPLOAD_FOLDER, f"{media_key}.mp4"),  # 带扩展名的路径
                os.path.join(VIDEOS_FOLDER, media_key),  # 在videos目录
                os.path.join(VIDEOS_FOLDER, f"{media_key}.mp4")  # 带扩展名在videos目录
            ]
            
            # 尝试查找匹配的文件(支持不同扩展名)
            media_path = None
            for base_path in local_paths:
                # 检查没有扩展名的完整匹配
                if os.path.exists(base_path) and os.path.isfile(base_path):
                    media_path = base_path
                    break
                
                # 检查各种可能的扩展名
                for ext in ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', 'mp3', 'wav', 'ogg', 'flac', 'm4a']:
                    if not base_path.endswith(f".{ext}"):  # 避免重复添加扩展名
                        test_path = f"{os.path.splitext(base_path)[0]}.{ext}"
                        if os.path.exists(test_path) and os.path.isfile(test_path):
                            media_path = test_path
                            break
                            
                if media_path:
                    break
            
            if not media_path:
                raise FileNotFoundError(f"找不到与media_key: {media_key}匹配的本地媒体文件")
                
            logger.info(f"找到本地媒体文件: {media_path}")
            
        else:
            # 从URL下载媒体文件
            if not media_url or media_url.strip() == "":
                raise ValueError("未提供media_key或有效的media_url")
                
            self.update_state(state='DOWNLOADING', meta={
                'status': TASK_STATUS['DOWNLOADING'],
                'progress': 10
            })
            
            media_path = download_media(media_url, task_id)
        
        # 确定设备
        device = torch.device("cpu")
        
        if not options['cpu']:
            # 检查MPS加速
            if torch.backends.mps.is_available() and not options['no_mps']:
                try:
                    device = torch.device("mps")
                    logger.info("使用MPS加速")
                except Exception as e:
                    logger.warning(f"MPS初始化失败，回退到CPU: {e}")
                    device = torch.device("cpu")
            # 检查CUDA加速
            elif torch.cuda.is_available():
                device = torch.device("cuda")
                logger.info("使用CUDA加速")
        
        # 如果是视频文件，提取音频
        is_video = media_path.split('.')[-1].lower() in ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']
        
        if is_video:
            self.update_state(state='EXTRACTING', meta={
                'status': TASK_STATUS['EXTRACTING'],
                'progress': 30
            })
            audio_path = extract_audio(media_path)
        else:
            audio_path = media_path
        
        # 生成字幕
        self.update_state(state='TRANSCRIBING', meta={
            'status': TASK_STATUS['TRANSCRIBING'],
            'progress': 50
        })
        
        # 设置输出文件路径
        output_file = os.path.join(
            RESULT_FOLDER, 
            f"{task_id}.{options['format']}"
        )
        
        # 生成字幕
        subtitle_file = generate_subtitles(
            audio_file=audio_path,
            output_file=output_file,
            format_type=options['format'],
            model_name=options['model'],
            language=options['language'],
            max_line_length=options['max_line_length'],
            device=device
        )
        
        # OBS存储处理
        subtitle_url = f"/results/{os.path.basename(subtitle_file)}"
        obs_url = None
        
        if USE_OBS_STORAGE:
            # 上传到OBS
            success, result = obs_storage.upload_file(subtitle_file)
            if success:
                logger.info(f"字幕文件已上传到OBS: {result}")
                obs_url = result
            else:
                logger.error(f"上传字幕文件到OBS失败: {result}")
        
        # 读取生成的字幕文件
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            subtitle_content = f.read()
        
        # 将结果保存为JSON
        result = {
            'task_id': task_id,
            'status': 'SUCCESS',
            'subtitle_file': os.path.basename(subtitle_file),
            'subtitle_content': subtitle_content,
            'media_url': media_url,
            'options': options
        }
        
        # 添加OBS URL（如果有）
        if obs_url:
            result['obs_url'] = obs_url
        
        with open(os.path.join(RESULT_FOLDER, f"{task_id}.json"), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        response_data = {
            'status': TASK_STATUS['SUCCESS'],
            'progress': 100,
            'task_id': task_id,
            'subtitle_file': os.path.basename(subtitle_file),
            'subtitle_url': subtitle_url
        }
        
        # 添加OBS URL到响应（如果有）
        if obs_url:
            response_data['obs_url'] = obs_url
            
        return response_data
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        return {
            'status': TASK_STATUS['FAILURE'],
            'error': str(e)
        } 