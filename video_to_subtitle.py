#!/usr/bin/env python3
"""
从视频到字幕的修复版脚本 - 解决ffmpeg路径问题，支持GPU加速
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
import torch

def check_gpu():
    """检查系统中可用的GPU加速选项"""
    has_cuda = torch.cuda.is_available()
    has_mps = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
    
    if has_cuda:
        cuda_devices = [f"CUDA:{i} ({torch.cuda.get_device_name(i)})" for i in range(torch.cuda.device_count())]
        print(f"检测到CUDA加速可用: {', '.join(cuda_devices)}")
        return "cuda", cuda_devices
    elif has_mps:
        print("检测到Apple Silicon MPS加速可用")
        return "mps", ["MPS"]
    else:
        print("未检测到GPU加速，将使用CPU处理")
        return "cpu", []

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
    
    # 添加GPU相关参数
    device_group = parser.add_argument_group('GPU加速选项')
    device_group.add_argument("--device", 
                        choices=["auto", "cpu", "cuda", "mps"], default="auto",
                        help="处理设备: auto=自动选择, cpu=仅使用CPU, cuda=使用NVIDIA GPU, mps=使用Apple Silicon GPU")
    device_group.add_argument("--cuda-device", type=int, default=0,
                        help="当有多个CUDA设备时，指定要使用的设备ID (默认: 0)")
    device_group.add_argument("--fp16", action="store_true", 
                        help="使用半精度浮点运算（更快，但在某些GPU上可能不稳定）")
    device_group.add_argument("--no-gpu", action="store_true",
                        help="强制使用CPU，即使有GPU可用")
    
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
        
        # 确定处理设备
        print("\n检查GPU加速状态:")
        gpu_type, available_devices = check_gpu()
        
        if args.no_gpu:
            device = "cpu"
            print("已强制使用CPU处理")
        elif args.device == "auto":
            if gpu_type == "cpu" or args.model in ["tiny", "base"] and not args.fp16:
                # 小模型在CPU上可能更快
                device = "cpu"
                print("自动选择: 使用CPU处理")
            else:
                device = gpu_type
                if device == "cuda":
                    device_id = min(args.cuda_device, torch.cuda.device_count() - 1)
                    device = f"cuda:{device_id}"
                    print(f"自动选择: 使用NVIDIA GPU加速 ({device})")
                elif device == "mps":
                    print("自动选择: 使用Apple Silicon GPU加速")
        else:
            # 用户指定设备
            if args.device == "cuda" and gpu_type != "cuda":
                print("警告: 请求使用CUDA但未检测到NVIDIA GPU，将使用CPU")
                device = "cpu"
            elif args.device == "mps" and gpu_type != "mps":
                print("警告: 请求使用MPS但未检测到Apple Silicon GPU，将使用CPU")
                device = "cpu"
            else:
                device = args.device
                if device == "cuda":
                    device_id = min(args.cuda_device, torch.cuda.device_count() - 1)
                    device = f"cuda:{device_id}"
                    print(f"使用NVIDIA GPU加速 ({device})")
                elif device == "mps":
                    print("使用Apple Silicon GPU加速")
                else:
                    print("使用CPU处理")
        
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
        print(f"正在加载Whisper模型({args.model})到{device}设备...")
        try:
            model = whisper.load_model(args.model, device=device)
            print(f"模型加载完成")
        except Exception as model_error:
            print(f"在{device}上加载模型失败: {model_error}")
            print("尝试在CPU上加载模型...")
            model = whisper.load_model(args.model, device="cpu")
            print("已在CPU上加载模型")
            device = "cpu"
        
        # 转录选项
        transcribe_options = {
            "word_timestamps": True,
        }
        
        # 如果指定了FP16，并且在GPU上运行
        if args.fp16 and device != "cpu":
            transcribe_options["fp16"] = True
            print("已启用半精度(FP16)加速")
        
        if args.language:
            transcribe_options["language"] = args.language
        
        # 进行转录
        print(f"正在使用Whisper处理音频: {audio_file}")
        print(f"转录设置: {transcribe_options}")
        
        # 显示处理进度提示
        print("\n处理中，请耐心等待...")
        print(f"注意: 较大的模型和较长的音频文件需要更多时间处理")
        if device == "cpu":
            print("在CPU上处理可能需要较长时间，特别是使用大型模型时")
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 执行转录
        result = model.transcribe(audio_file, **transcribe_options)
        
        # 计算总时间
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        print(f"\n转录完成！用时: {int(minutes)}分{int(seconds)}秒")
        
        # 将结果写入字幕文件
        print(f"正在生成{args.format}格式字幕文件...")
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
        
        # 如果使用CPU处理了large模型，给出提示
        if device == "cpu" and args.model == "large":
            print("\n注意: 您在CPU上使用了large模型，这可能比较慢。")
            print("如果您有兼容的GPU，建议使用GPU加速以提高处理速度。")
        
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