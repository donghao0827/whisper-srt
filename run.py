import whisper
import argparse
import torch
from datetime import timedelta

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{td}".split('.')[0] + f",{ms:03d}"

def generate_subtitles(audio_file, output_file=None, model_name="base", language=None, device=None):
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
    
    # Transcribe the audio file with word-level timestamps
    print(f"Transcribing {audio_file} with {model_name} model on {device}...")
    
    try:
        result = model.transcribe(audio_file, **transcribe_options)
    except Exception as e:
        print(f"Error using {device} for transcription, falling back to CPU: {e}")
        device = torch.device("cpu")
        model = whisper.load_model(model_name, device=device)
        result = model.transcribe(audio_file, **transcribe_options)
    
    # If no output file specified, use the audio filename with .srt extension
    if output_file is None:
        output_file = audio_file.rsplit(".", 1)[0] + ".srt"
    
    # Process segments and write SRT file
    with open(output_file, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(result["segments"], start=1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            # Write SRT entry
            srt_file.write(f"{i}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{text}\n\n")
    
    print(f"Subtitles saved to {output_file}")
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SRT subtitles from audio using Whisper")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("--output", "-o", help="Output SRT file path (default: same as audio file with .srt extension)")
    parser.add_argument("--model", "-m", default="base", help="Whisper model size: tiny, base, small, medium, large (default: base)")
    parser.add_argument("--language", "-l", help="Language code (ISO 639-1) for transcription (e.g., 'zh' for Chinese)")
    parser.add_argument("--no-mps", action="store_true", help="Disable MPS acceleration even if available")
    parser.add_argument("--cpu", action="store_true", help="Force using CPU even if GPU is available")
    
    args = parser.parse_args()
    
    # Determine device to use
    device = torch.device("cpu")
    
    if not args.cpu:
        # Check for MPS (Apple Silicon GPU)
        if torch.backends.mps.is_available() and not args.no_mps:
            try:
                device = torch.device("mps")
                print("Using MPS acceleration on Apple Silicon")
            except Exception as e:
                print(f"Error initializing MPS device, falling back to CPU: {e}")
                device = torch.device("cpu")
        # Check for CUDA (NVIDIA GPU)
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            print("Using CUDA acceleration on NVIDIA GPU")
        else:
            print("No GPU acceleration available, using CPU")
    else:
        print("Forced CPU usage as requested")
    
    generate_subtitles(args.audio_file, args.output, args.model, args.language, device)
