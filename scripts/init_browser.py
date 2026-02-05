#!/usr/bin/env python3
"""初始化浏览器并完成首次登录"""

import sys
sys.path.append('.')

from src.browser_manager import BrowserManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("\n" + "="*60)
    print("QDII基金限额监控系统 - 初始化")
    print("="*60 + "\n")
    
    manager = BrowserManager()
    
    try:
        # 启动浏览器
        manager.start()
        
        # 检查登录状态
        if manager.check_login_status():
            print("\n✓ 检测到已登录状态,无需重新登录")
        else:
            print("\n需要登录天天基金账户")
            if manager.wait_for_manual_login():
                print("\n✓ 登录成功!浏览器状态已保存")
            else:
                print("\n✗ 登录失败或超时")
                return
        
        print("\n" + "="*60)
        print("初始化完成!您现在可以:")
        print("1. 运行 python scripts/daily_search.py 同步基金到自选")
        print("2. 运行 python scripts/quota_monitor.py 检查限额")
        print("3. 运行 python run.py 启动完整监控")
        print("="*60 + "\n")
        
        input("按回车键关闭浏览器...")
        
    finally:
        manager.close()

if __name__ == "__main__":
    main()