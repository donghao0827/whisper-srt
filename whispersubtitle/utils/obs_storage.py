"""
OBS对象存储工具
"""

import os
import logging
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from whispersubtitle.config.settings import (
    USE_OBS_STORAGE,
    OBS_ENDPOINT,
    OBS_ACCESS_KEY,
    OBS_SECRET_KEY,
    OBS_SUBTITLES_BUCKET,
    OBS_REGION
)

logger = logging.getLogger(__name__)

class OBSStorage:
    """对象存储服务工具类"""
    
    def __init__(self):
        """初始化OBS客户端"""
        self.enabled = USE_OBS_STORAGE
        
        if not self.enabled:
            logger.info("OBS存储未启用")
            return
            
        try:
            # 创建S3/OBS客户端(使用boto3兼容S3/OBS API)
            self.client = boto3.client(
                's3',
                endpoint_url=OBS_ENDPOINT,
                aws_access_key_id=OBS_ACCESS_KEY,
                aws_secret_access_key=OBS_SECRET_KEY,
                region_name=OBS_REGION
            )
            
            # 确保桶存在
            self._ensure_bucket_exists()
            
            logger.info(f"OBS存储已初始化，使用桶: {OBS_SUBTITLES_BUCKET}")
        except Exception as e:
            logger.error(f"初始化OBS存储失败: {str(e)}")
            self.enabled = False
    
    def _ensure_bucket_exists(self):
        """确保桶存在，如不存在则创建"""
        try:
            self.client.head_bucket(Bucket=OBS_SUBTITLES_BUCKET)
        except ClientError as e:
            # 如果桶不存在，则创建
            if e.response['Error']['Code'] == '404':
                self.client.create_bucket(Bucket=OBS_SUBTITLES_BUCKET)
                logger.info(f"已创建桶: {OBS_SUBTITLES_BUCKET}")
            else:
                # 其他错误
                logger.error(f"检查桶存在性时出错: {str(e)}")
                raise
    
    def upload_file(self, local_file_path: str, object_key: Optional[str] = None) -> Tuple[bool, str]:
        """
        上传文件到OBS
        
        参数:
            local_file_path: 本地文件路径
            object_key: 对象键名，不指定则使用文件名
            
        返回:
            (成功标志, 对象URL或错误信息)
        """
        if not self.enabled:
            return False, "OBS存储未启用"
            
        if not os.path.exists(local_file_path):
            return False, f"本地文件不存在: {local_file_path}"
        
        # 如果未指定对象键，使用文件名
        if object_key is None:
            object_key = os.path.basename(local_file_path)
        
        try:
            # 上传文件
            self.client.upload_file(
                local_file_path, 
                OBS_SUBTITLES_BUCKET, 
                object_key,
                ExtraArgs={'ContentType': self._get_content_type(local_file_path)}
            )
            
            # 生成对象URL
            object_url = f"{OBS_ENDPOINT}/{OBS_SUBTITLES_BUCKET}/{object_key}"
            if OBS_ENDPOINT.startswith('http'):
                # 确保不重复http前缀
                object_url = f"{OBS_ENDPOINT}/{OBS_SUBTITLES_BUCKET}/{object_key}"
            else:
                object_url = f"https://{OBS_ENDPOINT}/{OBS_SUBTITLES_BUCKET}/{object_key}"
                
            logger.info(f"文件已上传到OBS: {object_url}")
            return True, object_url
        except Exception as e:
            error_msg = f"上传文件到OBS失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _get_content_type(self, file_path: str) -> str:
        """根据文件扩展名获取内容类型"""
        ext = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            '.srt': 'application/x-subrip',
            '.vtt': 'text/vtt',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.flv': 'video/x-flv',
            '.wmv': 'video/x-ms-wmv',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        
        return content_types.get(ext, 'application/octet-stream')

# 创建单例实例
obs_storage = OBSStorage() 