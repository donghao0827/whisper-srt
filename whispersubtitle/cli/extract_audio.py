"""
音频提取命令行工具
"""

import os
import argparse
import subprocess
from pathlib import Path

def extract_audio(video_file, output_audio=None, audio_format="mp3", audio_quality="192k", sample_rate=44100):
    """
    使用ffmpeg从视频文件提取音频
    
    参数:
    - video_file: 视频文件路径
    - output_audio: 输出音频文件路径（默认：根据视频文件名生成）
    - audio_format: 音频格式（默认：mp3，支持：mp3, wav, ogg, flac, m4a）
    - audio_quality: 音频比特率（默认：192k）
    - sample_rate: 采样率（默认：44100 Hz）
    
    返回:
    - 提取的音频文件路径
    """
    if output_audio is None:
        output_audio = os.path.splitext(video_file)[0] + f".{audio_format}"
    
    print(f"正在从 {video_file} 提取音频...")
    
    # 构建ffmpeg命令
    ffmpeg_cmd = [
        "ffmpeg", "-i", video_file, 
        "-y",  # 覆盖已存在的输出文件
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
    
    try:
        print(f"执行命令: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(
            ffmpeg_cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"音频提取成功: {output_audio}")
        return output_audio
    except subprocess.CalledProcessError as e:
        print(f"提取音频时出错: {e}")
        print(f"FFmpeg错误信息: {e.stderr.decode('utf-8')}")
        raise

def batch_extract(input_dir, output_dir=None, audio_format="mp3", audio_quality="192k", sample_rate=44100):
    """从指定目录中批量提取所有视频的音频"""
    input_path = Path(input_dir)
    
    if not input_path.exists() or not input_path.is_dir():
        raise ValueError(f"输入目录不存在: {input_dir}")
    
    if output_dir is None:
        output_dir = input_dir
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    # 支持的视频扩展名
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    
    # 计数器
    total_videos = 0
    successful = 0
    failed = 0
    
    print(f"正在扫描目录 {input_dir} 中的视频文件...")
    
    # 遍历目录中的所有文件
    for file_path in input_path.glob('**/*'):
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            total_videos += 1
            output_path = Path(output_dir) / f"{file_path.stem}.{audio_format}"
            
            try:
                print(f"\n处理文件 [{total_videos}]: {file_path}")
                extract_audio(
                    str(file_path), 
                    str(output_path), 
                    audio_format, 
                    audio_quality, 
                    sample_rate
                )
                successful += 1
            except Exception as e:
                failed += 1
                print(f"处理 {file_path} 时出错: {e}")
    
    print(f"\n批量处理完成！")
    print(f"总计处理: {total_videos} 个视频文件")
    print(f"成功: {successful}")
    print(f"失败: {failed}")

def main():
    parser = argparse.ArgumentParser(description="使用ffmpeg从视频提取音频")
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 单文件提取命令
    single_parser = subparsers.add_parser("extract", help="从单个视频文件提取音频")
    single_parser.add_argument("video_file", help="输入视频文件路径")
    single_parser.add_argument("-o", "--output", help="输出音频文件路径")
    single_parser.add_argument("-f", "--format", choices=["mp3", "wav", "ogg", "flac", "m4a"], 
                               default="mp3", help="音频格式 (默认: mp3)")
    single_parser.add_argument("-q", "--quality", default="192k", 
                               help="音频比特率，用于有损格式 (默认: 192k)")
    single_parser.add_argument("-r", "--sample-rate", type=int, default=44100, 
                               help="采样率，单位Hz (默认: 44100)")
    
    # 批量提取命令
    batch_parser = subparsers.add_parser("batch", help="批量从目录中的视频文件提取音频")
    batch_parser.add_argument("input_dir", help="输入目录路径（包含视频文件）")
    batch_parser.add_argument("-o", "--output-dir", help="输出目录路径（存放生成的音频文件）")
    batch_parser.add_argument("-f", "--format", choices=["mp3", "wav", "ogg", "flac", "m4a"], 
                              default="mp3", help="音频格式 (默认: mp3)")
    batch_parser.add_argument("-q", "--quality", default="192k", 
                              help="音频比特率，用于有损格式 (默认: 192k)")
    batch_parser.add_argument("-r", "--sample-rate", type=int, default=44100, 
                              help="采样率，单位Hz (默认: 44100)")
    
    args = parser.parse_args()
    
    if args.command == "extract":
        try:
            extract_audio(
                args.video_file, 
                args.output, 
                args.format, 
                args.quality, 
                args.sample_rate
            )
        except Exception as e:
            print(f"错误: {e}")
            return 1
            
    elif args.command == "batch":
        try:
            batch_extract(
                args.input_dir, 
                args.output_dir, 
                args.format, 
                args.quality, 
                args.sample_rate
            )
        except Exception as e:
            print(f"错误: {e}")
            return 1
            
    else:
        parser.print_help()
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main()) 