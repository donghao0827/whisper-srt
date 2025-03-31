#!/usr/bin/env python3
import os
import sys
import argparse
import whisper
import torch
import pysrt
import datetime
import tempfile
import platform
import subprocess
from pathlib import Path
from tqdm import tqdm
import ffmpeg

# 默认目录
DEFAULT_INPUT_DIR = "videos"
DEFAULT_OUTPUT_DIR = "subtitles"

def format_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    td = datetime.timedelta(seconds=seconds)
    ms = int((td.microseconds / 1000) % 1000)
    return f"{td.seconds//3600:02d}:{(td.seconds//60)%60:02d}:{td.seconds%60:02d},{ms:03d}"

def create_srt_file(transcript, output_file):
    """Create an SRT file from Whisper transcript"""
    subs = pysrt.SubRipFile()
    
    for i, segment in enumerate(transcript['segments'], 1):
        start_time = format_time(segment['start'])
        end_time = format_time(segment['end'])
        text = segment['text'].strip()
        
        item = pysrt.SubRipItem(
            index=i,
            start=pysrt.SubRipTime.from_string(start_time),
            end=pysrt.SubRipTime.from_string(end_time),
            text=text
        )
        subs.append(item)
    
    subs.save(output_file, encoding='utf-8')
    return output_file

def check_ffmpeg():
    """Check if FFmpeg is installed using both ffmpeg-python and direct command check"""
    # 方法1: 尝试使用subprocess直接调用ffmpeg命令
    try:
        # 抑制输出，只检查命令是否存在
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=False  # 不要在命令失败时引发异常
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass  # 如果这种方法失败，尝试下一种方法
    
    # 方法2: 尝试使用ffmpeg-python库
    try:
        ffmpeg.input(os.devnull).output('-', format='null').run(capture_stdout=True, capture_stderr=True)
        return True
    except (ffmpeg.Error, FileNotFoundError):
        pass
    
    # 如果到这里仍未返回，说明两种方法都失败了
    return False

def extract_audio(video_path, target_path):
    """Extract audio from video file using ffmpeg"""
    try:
        # 尝试使用ffmpeg-python库
        try:
            (
                ffmpeg
                .input(video_path)
                .output(target_path, acodec='pcm_s16le', ac=1, ar='16k')
                .run(quiet=True, overwrite_output=True)
            )
            return target_path
        except (ffmpeg.Error, FileNotFoundError) as e:
            # 如果ffmpeg-python失败，尝试直接使用命令行
            print("尝试使用命令行ffmpeg...")
            result = subprocess.run([
                "ffmpeg", "-i", str(video_path), 
                "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16k",
                "-y", str(target_path)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return target_path
    except Exception as e:
        print(f"Error extracting audio: {str(e)}")
        raise

def get_device():
    """Get the appropriate device (CUDA, MPS, or CPU)"""
    if torch.cuda.is_available():
        return "cuda"
    # MPS (Apple Silicon) 有兼容性问题，强制使用CPU
    # elif torch.backends.mps.is_available() and platform.system() == "Darwin":
    #    return "mps"  # For Apple Silicon GPUs
    else:
        return "cpu"

def process_file(input_path, output_path, model, language, device):
    """Process a single file"""
    # Determine if input is audio or video
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    
    is_video = input_path.suffix.lower() in video_extensions
    is_audio = input_path.suffix.lower() in audio_extensions
    
    if not (is_video or is_audio):
        print(f"Warning: Unrecognized file extension {input_path.suffix}. Attempting to process anyway.")
    
    # If video, extract audio first
    temp_audio_path = None
    if is_video:
        print(f"Extracting audio from video: {input_path.name}...")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        
        try:
            extract_audio(str(input_path), temp_audio_path)
            audio_path = temp_audio_path
        except Exception as e:
            print(f"Error extracting audio: {str(e)}")
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            return False
    else:
        audio_path = str(input_path)
    
    # Transcribe with Whisper
    print(f"Transcribing: {input_path.name} with Whisper ({language})...")
    transcribe_options = {}
    
    if language:
        transcribe_options["language"] = language
    
    try:
        result = model.transcribe(audio_path, **transcribe_options)
        
        # Create SRT file
        print(f"Creating SRT file: {output_path}")
        create_srt_file(result, output_path)
        
        print(f"Completed: {input_path.name} -> {output_path}")
        return True
    except Exception as e:
        print(f"Error during transcription of {input_path.name}: {str(e)}")
        return False
    finally:
        # Clean up temporary file if created
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)

def ensure_dir(dir_path):
    """Ensure directory exists, create if it doesn't"""
    path = Path(dir_path)
    if not path.exists():
        print(f"Creating directory: {path}")
        path.mkdir(parents=True, exist_ok=True)
    return path

def main():
    # Check for FFmpeg before continuing
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed or not found in PATH.")
        print("Please install FFmpeg:")
        print("- macOS: brew install ffmpeg")
        print("- Windows: Download from https://ffmpeg.org/download.html")
        print("- Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg")
        print("\n如果您已经安装了FFmpeg，请确保它在系统PATH中，或尝试以下操作:")
        print("- 重新启动终端/命令提示符")
        print("- 检查ffmpeg命令是否可在终端中运行 (输入 'ffmpeg -version')")
        print("- macOS上，您可能需要运行: 'brew link --overwrite ffmpeg'")
        return 1

    # Create argument parser
    parser = argparse.ArgumentParser(description="Convert audio/video to SRT subtitles using Whisper")
    
    # Define input file group (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input-file", help="Path to a single audio or video file")
    input_group.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help=f"Path to directory containing audio or video files (default: {DEFAULT_INPUT_DIR})")
    
    # Other arguments
    parser.add_argument("--output", help="Output SRT file path (when using --input-file)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"Output directory for SRT files (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size (default: small)")
    parser.add_argument("--language", default="zh", help="Language code (e.g., 'en', 'zh'). Default: zh (Chinese)")
    parser.add_argument("--device", choices=["cuda", "cpu", "mps", "auto"], default="auto", 
                        help="Device to use for inference (default: auto)")
    parser.add_argument("--no-gpu", action="store_true", help="Force CPU usage even if GPU is available")
    args = parser.parse_args()
    
    # Handle backward compatibility for positional argument
    if len(sys.argv) > 1 and not any(arg.startswith('--') for arg in sys.argv[1:2]):
        args.input_file = sys.argv[1]
    
    # Determine device to use
    if args.no_gpu:
        device = "cpu"
        print("Forcing CPU usage as requested")
    elif args.device != "auto":
        device = args.device
    else:
        device = get_device()
    
    # Print system information
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"PyTorch: {torch.__version__}")
    print(f"Device: {device}")
    
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA: {torch.version.cuda}")
    
    # Load Whisper model
    print(f"Loading Whisper model: {args.model} (device: {device})")
    model = whisper.load_model(args.model, device=device)
    
    # Process based on input mode
    if args.input_file:
        # Process a single file
        input_path = Path(args.input_file).resolve()
        
        if not input_path.exists():
            print(f"Error: Input file '{input_path}' does not exist")
            return 1
        
        output_path = args.output if args.output else input_path.with_suffix('.srt')
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        ensure_dir(output_dir)
        
        success = process_file(input_path, output_path, model, args.language, device)
        return 0 if success else 1
        
    else:  # Default to directory mode if no input file specified
        # Process all files in a directory
        input_dir = ensure_dir(Path(args.input_dir).resolve())
        output_dir = ensure_dir(Path(args.output_dir).resolve())
        
        # Get all audio and video files in the input directory
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        supported_extensions = audio_extensions.union(video_extensions)
        
        media_files = [f for f in input_dir.glob('*') if f.is_file() and f.suffix.lower() in supported_extensions]
        
        if not media_files:
            print(f"No supported audio or video files found in '{input_dir}'")
            print(f"Please place your audio/video files in the '{args.input_dir}' directory")
            return 1
        
        # Process each file
        print(f"Found {len(media_files)} files to process")
        
        successful = 0
        failed = 0
        
        for input_file in media_files:
            output_file = output_dir / f"{input_file.stem}.srt"
            print(f"\nProcessing [{successful+failed+1}/{len(media_files)}]: {input_file.name}")
            
            if process_file(input_file, output_file, model, args.language, device):
                successful += 1
            else:
                failed += 1
        
        # Print summary
        print("\n" + "="*50)
        print(f"处理完成! 统计信息:")
        print(f"总文件数: {len(media_files)}")
        print(f"成功处理: {successful}")
        print(f"处理失败: {failed}")
        print("="*50)
        
        return 0 if failed == 0 else 1

if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        exit(130) 