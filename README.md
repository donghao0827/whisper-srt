# Whisper SRT

一个使用OpenAI的Whisper语音识别模型将音频/视频文件转换为SRT字幕的命令行工具。

## 系统要求

- Python 3.7+
- FFmpeg 已安装在系统中
- 推荐使用GPU以加快处理速度
  - 支持NVIDIA GPU (CUDA)
  - 支持Apple Silicon GPU (MPS)
  - 自动检测并使用最佳设备

## 平台兼容性

- **Windows**: 完全支持，自动检测NVIDIA GPU
- **macOS**: 完全支持，支持Intel和Apple Silicon，自动检测Apple GPU
- **Linux**: 完全支持，自动检测NVIDIA GPU

## 安装

1. 克隆此仓库
2. 安装FFmpeg（如果尚未安装）
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt update && sudo apt install ffmpeg`
   - Windows: [下载FFmpeg](https://ffmpeg.org/download.html)
3. 安装Python依赖:
   ```bash
   # 使用清华镜像源安装依赖
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

## 使用方法

### 处理单个文件

```bash
# 新的命令格式（推荐）
python whisper_srt.py --input-file <输入文件> [--output <输出文件.srt>] [--model <模型大小>] [--language <语言代码>] [--device <设备>]

# 兼容旧格式
python whisper_srt.py <输入文件> [--output <输出文件.srt>] [--model <模型大小>] [--language <语言代码>] [--device <设备>]
```

### 批量处理整个目录

```bash
# 带参数的方式
python whisper_srt.py --input-dir <输入目录> --output-dir <输出目录> [--model <模型大小>] [--language <语言代码>] [--device <设备>]

# 简化方式 - 使用默认目录
python whisper_srt.py
```

### 默认目录

程序会使用以下默认目录，如果这些目录不存在，程序会自动创建：

- 默认输入目录: `videos` - 放置您的音频/视频文件
- 默认输出目录: `subtitles` - 生成的SRT字幕文件将保存在这里

### 参数

- `--input-file`: 单个音频或视频文件路径
- `--input-dir`: 包含多个音频/视频文件的目录路径（默认：videos）
- `--output`: 单个输出SRT文件路径（使用`--input-file`时）
- `--output-dir`: SRT文件输出目录（默认：subtitles）
- `--language`: 语言代码（例如：'en'表示英语，'zh'表示中文等）（默认：zh）
- `--model`: Whisper模型大小（'tiny', 'base', 'small', 'medium', 'large'）（默认：'small'）
- `--device`: 用于推理的设备（'cuda', 'cpu', 'mps', 'auto'）（默认：'auto'）
- `--no-gpu`: 强制使用CPU，即使有GPU可用

## 示例

### 单文件处理

```bash
# 直接生成中文字幕 (language默认为zh，自动使用GPU如果可用)
python whisper_srt.py --input-file video.mp4

# 生成英文字幕
python whisper_srt.py --input-file video.mp4 --language en

# 使用更大的模型以提高准确性
python whisper_srt.py --input-file audio.mp3 --model medium --output transcript.srt

# 强制使用CPU处理
python whisper_srt.py --input-file video.mp4 --no-gpu
```

### 批量处理目录

```bash
# 最简单的方式 - 使用默认的videos和subtitles目录
python whisper_srt.py

# 处理videos目录中的所有视频，输出到subtitles目录
python whisper_srt.py --input-dir videos --output-dir subtitles

# 使用更大的模型并指定语言
python whisper_srt.py --input-dir podcast_folder --output-dir transcripts --model medium --language en

# 在Windows上处理特定路径
python whisper_srt.py --input-dir "C:\Users\Username\Videos" --output-dir "C:\Users\Username\Subtitles"
```

## 目录结构

使用默认设置时，您的项目目录应该像这样：

```
whisper-srt/
├── whisper_srt.py       # 主程序
├── requirements.txt     # 依赖列表
├── README.md           # 说明文档
├── videos/             # 默认输入目录 (放置您的视频/音频文件)
│   ├── video1.mp4
│   ├── video2.mp4
│   └── ...
└── subtitles/          # 默认输出目录 (生成的SRT文件)
    ├── video1.srt
    ├── video2.srt
    └── ...
```

## 支持的文件格式

- **音频**: .mp3, .wav, .flac, .aac, .ogg, .m4a
- **视频**: .mp4, .avi, .mov, .mkv, .webm, .flv

## 处理大文件

该工具经过优化，可以处理大型视频文件（2GB+）：
- 使用临时文件从视频中提取音频
- 智能内存管理
- 完善的错误处理
- 支持用户中断处理（Ctrl+C）

## 模型大小说明

- **tiny**: 最快，准确度最低(~1GB VRAM)
- **base**: 快速，低准确度(~1GB VRAM)
- **small**: 速度/准确度平衡(~2GB VRAM)
- **medium**: 更准确，较慢(~5GB VRAM)
- **large**: 最准确，最慢(~10GB VRAM) 