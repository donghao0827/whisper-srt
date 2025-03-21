#!/usr/bin/env python3
"""
WhisperSubtitle主入口脚本
"""

import argparse
import sys
from whispersubtitle.cli.video_to_subtitle import main as video_to_subtitle_main
from whispersubtitle.cli.extract_audio import main as extract_audio_main

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="WhisperSubtitle: 基于OpenAI Whisper的多功能字幕生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 添加视频到字幕处理子命令
    subtitle_parser = subparsers.add_parser("subtitle", help="视频到字幕处理")
    subtitle_parser.add_argument("args", nargs=argparse.REMAINDER, help="视频到字幕处理参数")
    
    # 添加音频提取子命令
    audio_parser = subparsers.add_parser("audio", help="音频提取")
    audio_parser.add_argument("args", nargs=argparse.REMAINDER, help="音频提取参数")
    
    # 添加API服务子命令
    api_parser = subparsers.add_parser("api", help="启动API服务")
    api_parser.add_argument("--host", default="0.0.0.0", help="API服务主机 (默认: 0.0.0.0)")
    api_parser.add_argument("--port", type=int, default=8000, help="API服务端口 (默认: 8000)")
    api_parser.add_argument("--reload", action="store_true", help="启用开发模式自动重载")
    
    # 解析参数
    args = parser.parse_args()
    
    if args.command == "subtitle":
        # 将参数传递给字幕处理脚本
        sys.argv = [sys.argv[0]] + args.args
        sys.exit(video_to_subtitle_main())
    
    elif args.command == "audio":
        # 将参数传递给音频提取脚本
        sys.argv = [sys.argv[0]] + args.args
        sys.exit(extract_audio_main())
    
    elif args.command == "api":
        # 启动API服务
        try:
            import uvicorn
            from whispersubtitle.api.app import app
            
            print(f"启动字幕生成API服务...")
            reload_arg = args.reload
            uvicorn.run("whispersubtitle.api.app:app", host=args.host, port=args.port, reload=reload_arg)
        except ImportError:
            print("错误: 未安装FastAPI或uvicorn，请运行 'pip install fastapi uvicorn'")
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(0)

if __name__ == "__main__":
    main() 