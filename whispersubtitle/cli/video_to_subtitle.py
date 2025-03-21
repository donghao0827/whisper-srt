"""
从视频到字幕的一站式处理工具
"""

import os
import argparse
from pathlib import Path
import torch

from whispersubtitle.core import extract_audio, generate_subtitles
from whispersubtitle.cli.extract_audio import extract_audio as cli_extract_audio

def process_video_to_subtitle(
    video_file,
    output_subtitle=None,
    subtitle_format="srt",
    model_name="base",
    language=None,
    max_line_length=None,
    audio_format="mp3",
    audio_quality="192k",
    sample_rate=44100,
    keep_audio=False,
    no_mps=False,
    cpu=False
):
    """
    一站式处理视频到字幕的完整流程
    
    参数:
    - video_file: 输入视频文件路径
    - output_subtitle: 输出字幕文件路径（默认根据视频文件名生成）
    - subtitle_format: 字幕格式, "srt" 或 "vtt"（默认：srt）
    - model_name: Whisper模型大小（默认：base）
    - language: 语言代码，如'zh'表示中文（默认：自动检测）
    - max_line_length: 字幕每行最大字符数（默认：None）
    - audio_format: 中间音频格式（默认：mp3）
    - audio_quality: 音频比特率（默认：192k）
    - sample_rate: 采样率（默认：44100 Hz）
    - keep_audio: 是否保留提取的音频文件（默认：False）
    - no_mps: 是否禁用MPS加速（默认：False）
    - cpu: 是否强制使用CPU（默认：False）
    
    返回:
    - 生成的字幕文件路径
    """
    print("=" * 50)
    print(f"开始处理视频到字幕的完整流程")
    print(f"输入视频：{video_file}")
    print("=" * 50)
    
    # 步骤1：提取音频
    print("\n第1步：从视频提取音频")
    audio_file = extract_audio(
        video_file=video_file, 
        audio_format=audio_format,
        audio_quality=audio_quality,
        sample_rate=sample_rate
    )
    print(f"音频提取完成：{audio_file}")
    
    # 步骤2：确定设备（CPU/GPU）
    device = torch.device("cpu")
    
    if not cpu:
        # 检查MPS加速（Apple Silicon）
        if torch.backends.mps.is_available() and not no_mps:
            try:
                device = torch.device("mps")
                print("使用MPS加速（Apple Silicon GPU）")
            except Exception as e:
                print(f"MPS初始化失败，回退到CPU: {e}")
                device = torch.device("cpu")
        # 检查CUDA加速（NVIDIA GPU）
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            print("使用CUDA加速（NVIDIA GPU）")
        else:
            print("无GPU加速可用，使用CPU处理")
    else:
        print("已强制使用CPU")
    
    # 步骤3：设置输出字幕文件路径
    if output_subtitle is None:
        output_subtitle = os.path.splitext(video_file)[0] + f".{subtitle_format}"
    
    # 步骤4：生成字幕
    print("\n第2步：使用Whisper生成字幕")
    print(f"使用模型：{model_name}，设备：{device}")
    subtitle_file = generate_subtitles(
        audio_file=audio_file,
        output_file=output_subtitle,
        format_type=subtitle_format,
        model_name=model_name,
        language=language,
        max_line_length=max_line_length,
        device=device
    )
    
    # 步骤5：清理（如果不保留音频文件）
    if not keep_audio and audio_file != video_file:  # 确保不删除原始输入（如果输入就是音频）
        try:
            os.remove(audio_file)
            print(f"\n已删除临时音频文件：{audio_file}")
        except Exception as e:
            print(f"删除临时音频文件时出错：{e}")
    
    print("\n=" * 50)
    print(f"处理完成！")
    print(f"字幕文件已生成：{subtitle_file}")
    print("=" * 50)
    
    return subtitle_file

def batch_process(
    input_dir,
    output_dir=None,
    subtitle_format="srt",
    model_name="base",
    language=None,
    max_line_length=None,
    audio_format="mp3",
    audio_quality="192k",
    sample_rate=44100,
    keep_audio=False,
    no_mps=False,
    cpu=False
):
    """从指定目录中批量处理所有视频，生成字幕"""
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
    
    print(f"\n开始扫描目录 {input_dir} 中的视频文件...")
    
    # 遍历目录中的所有文件
    for file_path in input_path.glob('**/*'):
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            total_videos += 1
            output_subtitle = Path(output_dir) / f"{file_path.stem}.{subtitle_format}"
            
            try:
                print(f"\n处理文件 [{total_videos}]: {file_path}")
                process_video_to_subtitle(
                    video_file=str(file_path),
                    output_subtitle=str(output_subtitle),
                    subtitle_format=subtitle_format,
                    model_name=model_name,
                    language=language,
                    max_line_length=max_line_length,
                    audio_format=audio_format,
                    audio_quality=audio_quality,
                    sample_rate=sample_rate,
                    keep_audio=keep_audio,
                    no_mps=no_mps,
                    cpu=cpu
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
    parser = argparse.ArgumentParser(description="从视频到字幕的一站式处理工具")
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 单文件处理命令
    single_parser = subparsers.add_parser("single", help="处理单个视频文件")
    single_parser.add_argument("video_file", help="输入视频文件路径")
    single_parser.add_argument("-o", "--output", help="输出字幕文件路径")
    single_parser.add_argument("-f", "--format", choices=["srt", "vtt"], 
                               default="srt", help="字幕格式 (默认: srt)")
    single_parser.add_argument("-m", "--model", default="base", 
                               help="Whisper模型大小: tiny, base, small, medium, large (默认: base)")
    single_parser.add_argument("-l", "--language", help="语言代码，如'zh'表示中文（不填则自动检测）")
    single_parser.add_argument("--max-line-length", type=int, help="字幕每行最大字符数")
    single_parser.add_argument("--audio-format", choices=["mp3", "wav", "ogg", "flac", "m4a"], 
                               default="mp3", help="中间音频格式 (默认: mp3)")
    single_parser.add_argument("--audio-quality", default="192k", 
                               help="音频比特率，用于有损格式 (默认: 192k)")
    single_parser.add_argument("--sample-rate", type=int, default=44100, 
                               help="采样率，单位Hz (默认: 44100)")
    single_parser.add_argument("--keep-audio", action="store_true", 
                               help="保留提取的音频文件")
    single_parser.add_argument("--no-mps", action="store_true",
                               help="禁用MPS加速")
    single_parser.add_argument("--cpu", action="store_true",
                               help="强制使用CPU，即使有GPU可用")
    
    # 批量处理命令
    batch_parser = subparsers.add_parser("batch", help="批量处理目录中的视频文件")
    batch_parser.add_argument("input_dir", help="输入目录路径（包含视频文件）")
    batch_parser.add_argument("-o", "--output-dir", help="输出目录路径（存放生成的字幕文件）")
    batch_parser.add_argument("-f", "--format", choices=["srt", "vtt"], 
                              default="srt", help="字幕格式 (默认: srt)")
    batch_parser.add_argument("-m", "--model", default="base", 
                              help="Whisper模型大小: tiny, base, small, medium, large (默认: base)")
    batch_parser.add_argument("-l", "--language", help="语言代码，如'zh'表示中文（不填则自动检测）")
    batch_parser.add_argument("--max-line-length", type=int, help="字幕每行最大字符数")
    batch_parser.add_argument("--audio-format", choices=["mp3", "wav", "ogg", "flac", "m4a"], 
                              default="mp3", help="中间音频格式 (默认: mp3)")
    batch_parser.add_argument("--audio-quality", default="192k", 
                              help="音频比特率，用于有损格式 (默认: 192k)")
    batch_parser.add_argument("--sample-rate", type=int, default=44100, 
                              help="采样率，单位Hz (默认: 44100)")
    batch_parser.add_argument("--keep-audio", action="store_true", 
                              help="保留提取的音频文件")
    batch_parser.add_argument("--no-mps", action="store_true",
                              help="禁用MPS加速")
    batch_parser.add_argument("--cpu", action="store_true",
                              help="强制使用CPU，即使有GPU可用")
    
    # 仅提取音频命令
    extract_parser = subparsers.add_parser("extract", help="仅从视频提取音频")
    extract_parser.add_argument("video_file", help="输入视频文件路径")
    extract_parser.add_argument("-o", "--output", help="输出音频文件路径")
    extract_parser.add_argument("-f", "--format", choices=["mp3", "wav", "ogg", "flac", "m4a"], 
                                default="mp3", help="音频格式 (默认: mp3)")
    extract_parser.add_argument("-q", "--quality", default="192k", 
                                help="音频比特率，用于有损格式 (默认: 192k)")
    extract_parser.add_argument("-r", "--sample-rate", type=int, default=44100, 
                                help="采样率，单位Hz (默认: 44100)")
    
    args = parser.parse_args()
    
    if args.command == "single":
        try:
            process_video_to_subtitle(
                video_file=args.video_file,
                output_subtitle=args.output,
                subtitle_format=args.format,
                model_name=args.model,
                language=args.language,
                max_line_length=args.max_line_length,
                audio_format=args.audio_format,
                audio_quality=args.audio_quality,
                sample_rate=args.sample_rate,
                keep_audio=args.keep_audio,
                no_mps=args.no_mps,
                cpu=args.cpu
            )
        except Exception as e:
            print(f"错误: {e}")
            return 1
            
    elif args.command == "batch":
        try:
            batch_process(
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                subtitle_format=args.format,
                model_name=args.model,
                language=args.language,
                max_line_length=args.max_line_length,
                audio_format=args.audio_format,
                audio_quality=args.audio_quality,
                sample_rate=args.sample_rate,
                keep_audio=args.keep_audio,
                no_mps=args.no_mps,
                cpu=args.cpu
            )
        except Exception as e:
            print(f"错误: {e}")
            return 1
            
    elif args.command == "extract":
        try:
            cli_extract_audio(
                args.video_file,
                args.output,
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