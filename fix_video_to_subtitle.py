#!/usr/bin/env python3
"""
从视频到字幕的修复版脚本 - 解决ffmpeg路径问题
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
import torch

# 在此处下载ffmpeg，解决路径问题
def ensure_ffmpeg():
    """确保系统中有ffmpeg可用，如果没有则下载一个便携版"""
    try:
        # 尝试使用现有的ffmpeg
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        print("系统中已安装FFmpeg，继续处理...")
        return "ffmpeg", None
    except (subprocess.SubprocessError, FileNotFoundError):
        print("系统中未检测到FFmpeg，正在下载便携版...")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        ffmpeg_zip = os.path.join(temp_dir, "ffmpeg.zip")
        ffmpeg_exe = os.path.join(temp_dir, "ffmpeg.exe")
        ffmpeg_bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_bin")
        os.makedirs(ffmpeg_bin_dir, exist_ok=True)
        
        # 手动下载FFmpeg并放入ffmpeg_bin目录
        print(f"正在创建FFmpeg可执行文件目录: {ffmpeg_bin_dir}")
        
        # 使用Python内置功能下载
        try:
            import urllib.request
            print("使用Python下载FFmpeg...")
            
            # 使用不同的下载链接
            ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            print(f"开始下载FFmpeg: {ffmpeg_url}")
            print(f"保存到: {ffmpeg_zip}")
            
            # 下载文件
            urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
            
            print("下载完成，开始解压...")
            
            # 使用PowerShell解压文件
            extract_cmd = f'powershell -Command "Expand-Archive -Path \'{ffmpeg_zip}\' -DestinationPath \'{temp_dir}\' -Force"'
            subprocess.run(extract_cmd, shell=True, check=True)
            
            # 找到ffmpeg.exe和ffprobe.exe
            ffmpeg_exe_path = None
            ffprobe_exe_path = None
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower() == "ffmpeg.exe":
                        src_ffmpeg = os.path.join(root, file)
                        dst_ffmpeg = os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")
                        # 复制文件
                        import shutil
                        shutil.copy2(src_ffmpeg, dst_ffmpeg)
                        print(f"已复制FFmpeg到: {dst_ffmpeg}")
                        ffmpeg_exe_path = dst_ffmpeg
                    
                    elif file.lower() == "ffprobe.exe":
                        src_ffprobe = os.path.join(root, file)
                        dst_ffprobe = os.path.join(ffmpeg_bin_dir, "ffprobe.exe")
                        # 复制文件
                        import shutil
                        shutil.copy2(src_ffprobe, dst_ffprobe)
                        print(f"已复制FFprobe到: {dst_ffprobe}")
                        ffprobe_exe_path = dst_ffprobe
            
            if not ffmpeg_exe_path:
                raise Exception("无法在解压后的文件中找到ffmpeg.exe")
                
            # 返回ffmpeg路径以及bin目录路径（用于添加到环境变量）
            return ffmpeg_exe_path, ffmpeg_bin_dir
            
        except Exception as e:
            print(f"下载FFmpeg时出错: {e}")
            
            # 如果下载失败，尝试使用自行下载的FFmpeg
            print("\n无法自动下载FFmpeg。请按照以下步骤手动设置FFmpeg:")
            print("1. 访问 https://www.gyan.dev/ffmpeg/builds/ 下载 'ffmpeg-release-essentials.zip'")
            print("2. 解压文件，将bin目录中的ffmpeg.exe和ffprobe.exe复制到当前目录下新建的ffmpeg_bin文件夹中")
            print("3. 再次运行此脚本")
            print("\n如果您已有FFmpeg，请将其路径添加到系统PATH中，或将ffmpeg.exe复制到项目根目录下的ffmpeg_bin文件夹\n")
            
            # 检查是否已经存在ffmpeg.exe
            local_ffmpeg = os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")
            if os.path.exists(local_ffmpeg):
                print(f"找到本地FFmpeg: {local_ffmpeg}")
                return local_ffmpeg, ffmpeg_bin_dir
                
            sys.exit(1)

def extract_audio(ffmpeg_path, video_file, output_audio=None, audio_format="mp3", audio_quality="192k", sample_rate=44100):
    """
    使用ffmpeg从视频文件中提取音频
    """
    if output_audio is None:
        output_audio = os.path.splitext(video_file)[0] + f".{audio_format}"
    
    print(f"从视频提取音频: {video_file}")
    print(f"使用FFmpeg: {ffmpeg_path}")
    
    # 构建ffmpeg命令
    ffmpeg_cmd = [
        ffmpeg_path, 
        "-i", video_file, 
        "-y",  # 覆盖输出文件（如果存在）
    ]
    
    # 配置音频编码参数
    if audio_format == "mp3":
        ffmpeg_cmd.extend([
            "-codec:a", "libmp3lame", 
            "-b:a", audio_quality, 
            "-ar", str(sample_rate)
        ])
    elif audio_format == "wav":
        ffmpeg_cmd.extend([
            "-codec:a", "pcm_s16le", 
            "-ar", str(sample_rate)
        ])
    elif audio_format == "ogg":
        ffmpeg_cmd.extend([
            "-codec:a", "libvorbis", 
            "-b:a", audio_quality, 
            "-ar", str(sample_rate)
        ])
    elif audio_format == "flac":
        ffmpeg_cmd.extend([
            "-codec:a", "flac", 
            "-ar", str(sample_rate)
        ])
    elif audio_format == "m4a":
        ffmpeg_cmd.extend([
            "-codec:a", "aac", 
            "-b:a", audio_quality, 
            "-ar", str(sample_rate)
        ])
    else:
        # 默认参数
        ffmpeg_cmd.extend([
            "-q:a", "0", "-map", "a"
        ])
    
    # 添加输出文件
    ffmpeg_cmd.append(output_audio)
    
    print("执行命令:", " ".join(ffmpeg_cmd))
    
    try:
        subprocess.run(
            ffmpeg_cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"音频提取完成: {output_audio}")
        return output_audio
    except subprocess.CalledProcessError as e:
        print(f"提取音频时出错: {e}")
        # 输出ffmpeg错误信息
        print(f"FFmpeg stderr: {e.stderr.decode('utf-8')}")
        raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="从视频到字幕的修复版脚本")
    
    # 命令行参数
    parser.add_argument("video_file", help="输入视频文件路径")
    parser.add_argument("-o", "--output", help="输出字幕文件路径")
    parser.add_argument("-f", "--format", choices=["srt", "vtt"], 
                        default="srt", help="字幕格式 (默认: srt)")
    parser.add_argument("-m", "--model", default="base", 
                        help="Whisper模型大小: tiny, base, small, medium, large (默认: base)")
    parser.add_argument("-l", "--language", help="语言代码，如'zh'表示中文（不填则自动检测）")
    parser.add_argument("--keep-audio", action="store_true", 
                      help="保留提取的音频文件")
    
    args = parser.parse_args()
    
    # 解决路径问题：确保输入文件存在
    video_file = os.path.abspath(args.video_file)
    if not os.path.exists(video_file):
        print(f"错误: 找不到视频文件 '{video_file}'")
        print(f"当前工作目录: {os.getcwd()}")
        sys.exit(1)
    
    print("=" * 50)
    print(f"开始处理视频到字幕")
    print(f"输入视频: {video_file}")
    print("=" * 50)
    
    try:
        # 确保ffmpeg可用，并获取bin目录
        ffmpeg_path, ffmpeg_bin_dir = ensure_ffmpeg()
        
        # 如果有FFmpeg bin目录，添加到环境变量PATH中
        if ffmpeg_bin_dir:
            old_path = os.environ.get('PATH', '')
            os.environ['PATH'] = f"{ffmpeg_bin_dir}{os.pathsep}{old_path}"
            print(f"已将FFmpeg添加到环境变量: {ffmpeg_bin_dir}")
        
        # 步骤1：提取音频
        print("\n第1步：从视频提取音频")
        audio_file = extract_audio(
            ffmpeg_path=ffmpeg_path,
            video_file=video_file, 
            audio_format="mp3"
        )
        
        print("\n第2步：使用Whisper生成字幕")
        print(f"正在使用Whisper模型生成字幕，这可能需要一些时间...")
        print(f"模型: {args.model}, 语言: {args.language or '自动检测'}")
        
        # 导入whisper（放在这里以避免不必要的导入，如果ffmpeg失败的话）
        import whisper
        
        # 输出当前环境变量PATH，用于调试
        print(f"当前环境变量PATH: {os.environ.get('PATH', '')}")
        
        # 确定输出字幕文件路径
        if args.output:
            output_subtitle = args.output
        else:
            output_subtitle = os.path.splitext(video_file)[0] + f".{args.format}"
        
        # 加载Whisper模型
        model = whisper.load_model(args.model)
        
        # 转录选项
        transcribe_options = {"word_timestamps": True}
        if args.language:
            transcribe_options["language"] = args.language
        
        # 进行转录
        print(f"正在使用Whisper处理音频: {audio_file}")
        result = model.transcribe(audio_file, **transcribe_options)
        
        # 将结果写入字幕文件
        with open(output_subtitle, "w", encoding="utf-8") as subtitle_file:
            # 添加VTT格式的头
            if args.format == "vtt":
                subtitle_file.write("WEBVTT\n\n")
            
            # 处理每个片段
            for i, segment in enumerate(result["segments"]):
                start_time = segment["start"]
                end_time = segment["end"]
                text = segment["text"].strip()
                
                # 格式化时间戳
                if args.format == "srt":
                    start_str = format_timestamp(start_time, "srt")
                    end_str = format_timestamp(end_time, "srt")
                    subtitle_file.write(f"{i+1}\n")
                    subtitle_file.write(f"{start_str} --> {end_str}\n")
                else:  # vtt
                    start_str = format_timestamp(start_time, "vtt")
                    end_str = format_timestamp(end_time, "vtt")
                    subtitle_file.write(f"{start_str} --> {end_str}\n")
                
                subtitle_file.write(f"{text}\n\n")
        
        # 删除临时音频文件（如果不保留）
        if not args.keep_audio and os.path.exists(audio_file):
            os.remove(audio_file)
            print(f"已删除临时音频文件: {audio_file}")
        
        print("\n" + "=" * 50)
        print(f"处理完成！")
        print(f"字幕文件已生成: {output_subtitle}")
        print("=" * 50)
        
    except Exception as e:
        print(f"处理时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def format_timestamp(seconds, format_type="srt"):
    """将秒转换为时间戳格式"""
    from datetime import timedelta
    
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((td.microseconds / 1000))
    
    if format_type == "srt":
        # SRT格式: 00:00:00,000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    elif format_type == "vtt":
        # VTT格式: 00:00:00.000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    else:
        raise ValueError(f"不支持的格式类型: {format_type}")

if __name__ == "__main__":
    main() 