import whisper
import argparse
import os
import subprocess
import json
import torch
from datetime import timedelta

def format_timestamp(seconds, format_type="srt"):
    """Convert seconds to timestamp format"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((td.microseconds / 1000))
    
    if format_type == "srt":
        # SRT format: 00:00:00,000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    elif format_type == "vtt":
        # VTT format: 00:00:00.000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    else:
        raise ValueError(f"Unsupported format type: {format_type}")

def extract_audio(video_file, output_audio=None, audio_format="mp3", audio_quality="192k", sample_rate=44100):
    """
    Extract audio from video file using ffmpeg
    
    Parameters:
    - video_file: Path to video file
    - output_audio: Output audio file path (default: derived from video filename)
    - audio_format: Audio format (default: mp3, supported: mp3, wav, ogg, flac, m4a)
    - audio_quality: Audio bitrate for lossy formats (default: 192k)
    - sample_rate: Sample rate in Hz (default: 44100)
    
    Returns:
    - Path to extracted audio file
    """
    if output_audio is None:
        output_audio = os.path.splitext(video_file)[0] + f".{audio_format}"
    
    print(f"Extracting audio from {video_file}...")
    
    # 构建ffmpeg命令
    ffmpeg_cmd = [
        "ffmpeg", "-i", video_file, 
        "-y",  # Overwrite output file if it exists
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
        subprocess.run(
            ffmpeg_cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"Audio extracted to {output_audio}")
        return output_audio
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        # 输出ffmpeg错误信息
        print(f"FFmpeg stderr: {e.stderr.decode('utf-8')}")
        raise

def generate_subtitles(audio_file, output_file=None, format_type="srt", 
                       model_name="base", language=None, 
                       max_line_length=None, segment_length=None,
                       transcription_result=None, device=None):
    """
    Generate subtitles from audio file
    
    Parameters:
    - audio_file: Path to audio file
    - output_file: Path to output subtitle file (default: derived from audio file)
    - format_type: Subtitle format, 'srt' or 'vtt' (default: srt)
    - model_name: Whisper model size (default: base)
    - language: Language code for transcription (default: auto-detect)
    - max_line_length: Maximum characters per subtitle line (default: None)
    - segment_length: Target length of subtitle segments in seconds (default: None)
    - transcription_result: Pre-existing transcription result (default: None)
    - device: Computing device to use (default: None)
    """
    # If no transcription result is provided, create one
    if transcription_result is None:
        # Load the Whisper model with fallback to CPU if needed
        try:
            model = whisper.load_model(model_name, device=device)
        except Exception as e:
            print(f"Error loading model on {device}, falling back to CPU: {e}")
            device = torch.device("cpu")
            model = whisper.load_model(model_name, device=device)
        
        # Prepare transcription options
        transcribe_options = {
            "word_timestamps": True,
        }
        
        if language:
            transcribe_options["language"] = language
        
        # Transcribe the audio
        print(f"Transcribing {audio_file} with {model_name} model on {device}...")
        transcription_result = model.transcribe(audio_file, **transcribe_options)
    
    # If no output file specified, use the audio filename with appropriate extension
    if output_file is None:
        output_file = os.path.splitext(audio_file)[0] + f".{format_type}"
    
    # Process segments and write subtitle file
    with open(output_file, "w", encoding="utf-8") as subtitle_file:
        # Add header for VTT format
        if format_type == "vtt":
            subtitle_file.write("WEBVTT\n\n")
        
        for i, segment in enumerate(transcription_result["segments"], start=1):
            start_time = segment["start"]
            end_time = segment["end"]
            text = segment["text"].strip()
            
            # Apply max line length if specified
            if max_line_length and len(text) > max_line_length:
                # Simple line breaking at space nearest to max_line_length
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    if len(current_line) + len(word) + 1 > max_line_length and current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                
                if current_line:
                    lines.append(current_line)
                
                text = "\n".join(lines)
            
            # Format timestamps according to the subtitle format
            start_formatted = format_timestamp(start_time, format_type)
            end_formatted = format_timestamp(end_time, format_type)
            
            # Write entry in the appropriate format
            if format_type == "srt":
                subtitle_file.write(f"{i}\n")
                subtitle_file.write(f"{start_formatted} --> {end_formatted}\n")
                subtitle_file.write(f"{text}\n\n")
            elif format_type == "vtt":
                subtitle_file.write(f"{start_formatted} --> {end_formatted}\n")
                subtitle_file.write(f"{text}\n\n")
    
    print(f"Subtitles saved to {output_file}")
    return output_file

def export_json(result, output_file):
    """Export the full transcription result to a JSON file"""
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2)
    print(f"Full transcription data exported to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate subtitles from audio/video using Whisper")
    parser.add_argument("input_file", help="Path to input audio or video file")
    parser.add_argument("--output", "-o", help="Output subtitle file path")
    parser.add_argument("--format", "-f", choices=["srt", "vtt"], default="srt", 
                        help="Subtitle format (default: srt)")
    parser.add_argument("--model", "-m", default="base", 
                        help="Whisper model size: tiny, base, small, medium, large (default: base)")
    parser.add_argument("--language", "-l", help="Language code (ISO 639-1) for transcription")
    parser.add_argument("--max-line-length", type=int, help="Maximum characters per subtitle line")
    parser.add_argument("--segment-length", type=float, help="Target length of subtitle segments in seconds")
    parser.add_argument("--extract-only", action="store_true", help="Only extract audio from video without transcription")
    parser.add_argument("--export-json", help="Export full transcription data to JSON file")
    parser.add_argument("--no-mps", action="store_true", help="Disable MPS acceleration even if available")
    parser.add_argument("--cpu", action="store_true", help="Force using CPU even if GPU is available")
    parser.add_argument("--audio-format", default="mp3", choices=["mp3", "wav", "ogg", "flac", "m4a"],
                        help="Audio format for extraction (default: mp3)")
    parser.add_argument("--audio-quality", default="192k", help="Audio bitrate for lossy formats (default: 192k)")
    parser.add_argument("--sample-rate", type=int, default=44100, help="Sample rate in Hz (default: 44100)")
    
    args = parser.parse_args()
    
    input_file = args.input_file
    input_ext = os.path.splitext(input_file)[1].lower()
    
    # Check if input is a video file
    video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"]
    is_video = input_ext in video_extensions
    
    if is_video:
        # Extract audio from video
        audio_file = extract_audio(
            input_file, 
            audio_format=args.audio_format,
            audio_quality=args.audio_quality,
            sample_rate=args.sample_rate
        )
        if args.extract_only:
            print(f"Audio extracted to {audio_file}")
            exit(0)
    else:
        audio_file = input_file
    
    # Load the model with fallback to CPU if needed
    try:
        device = torch.device("cpu")
        
        if not args.cpu:
            # Check for MPS (Apple Silicon GPU)
            if torch.backends.mps.is_available() and not args.no_mps:
                device = torch.device("mps")
                print("Using MPS acceleration on Apple Silicon")
            # Check for CUDA (NVIDIA GPU)
            elif torch.cuda.is_available():
                device = torch.device("cuda")
                print("Using CUDA acceleration on NVIDIA GPU")
            else:
                print("No GPU acceleration available, using CPU")
        else:
            print("Forced CPU usage as requested")
            
        model = whisper.load_model(args.model, device=device)
    except Exception as e:
        print(f"Error loading model on {device}, falling back to CPU: {e}")
        device = torch.device("cpu")
        model = whisper.load_model(args.model, device=device)
    
    # Transcribe the audio
    transcribe_options = {
        "word_timestamps": True,
    }
    
    if args.language:
        transcribe_options["language"] = args.language
    
    print(f"Transcribing {audio_file} with {args.model} model on {device}...")
    
    try:
        result = model.transcribe(audio_file, **transcribe_options)
    except Exception as e:
        print(f"Error using {device} for transcription, falling back to CPU: {e}")
        device = torch.device("cpu")
        model = whisper.load_model(args.model, device=device)
        result = model.transcribe(audio_file, **transcribe_options)
    
    # Export to JSON if requested
    if args.export_json:
        export_json(result, args.export_json)
    
    # Generate subtitle file
    generate_subtitles(
        audio_file=audio_file,
        output_file=args.output,
        format_type=args.format,
        transcription_result=result,
        max_line_length=args.max_line_length,
        segment_length=args.segment_length,
        device=device
    ) 