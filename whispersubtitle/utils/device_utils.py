"""
设备相关工具函数
"""

import torch

def get_optimal_device(no_mps=False, cpu=False):
    """
    获取最优的计算设备
    
    参数:
    - no_mps: 是否禁用MPS加速（默认：False）
    - cpu: 是否强制使用CPU（默认：False）
    
    返回:
    - torch.device: 计算设备
    """
    device = torch.device("cpu")
    
    if cpu:
        return device
    
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
    
    return device 