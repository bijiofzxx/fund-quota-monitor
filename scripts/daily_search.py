#!/usr/bin/env python3
"""每日搜索新基金并加入自选"""

import sys
sys.path.append('.')

import yaml
from src.browser_manager import BrowserManager
from src.fund_searcher import FundSearcher
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./data/logs/daily_search.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    manager = BrowserManager()
    
    try:
        manager.start()
        
        # 检查登录
        if not manager.check_login_status():
            logging.error("未登录!直接登录或者 关闭程序运行 python scripts/init_browser.py")
            input("等待登陆中.... 回车确认登录继续运行")
        
        searcher = FundSearcher(manager, config)
        new_count = searcher.sync_favorites()
        
        logging.info(f"\n任务完成!新增 {new_count} 只基金")
        
    finally:
        manager.close()

if __name__ == "__main__":
    main()