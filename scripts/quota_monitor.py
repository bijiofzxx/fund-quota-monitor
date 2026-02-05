#!/usr/bin/env python3
"""监控自选基金限额"""

import sys
sys.path.append('.')

import yaml
from src.browser_manager import BrowserManager
from src.fund_collector import FundCollector
from src.quota_analyzer import QuotaAnalyzer
from src.notifier import Notifier
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./data/logs/quota_monitor.log', encoding='utf-8'),
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
            logging.error("未登录!请先运行 python scripts/init_browser.py")
            return
        
        # 采集数据
        collector = FundCollector(manager, config)
        df = collector.collect_quota_data()
        
        if df.empty:
            logging.warning("未采集到数据")
            return
        
        # 分析
        analyzer = QuotaAnalyzer(config)
        qualified_df, need_notify = analyzer.analyze(df)
        
        # 生成报告
        report = analyzer.generate_report(qualified_df)
        print("\n" + report)
        
        # 发送通知
        if need_notify:
            notifier = Notifier(config)
            subject = f"QDII基金限额提醒 - {len(qualified_df)}只基金符合条件"
            notifier.send(subject, report)
        else:
            logging.info("无需发送通知")
        
    finally:
        manager.close()

if __name__ == "__main__":
    main()