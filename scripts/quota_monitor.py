#!/usr/bin/env python3
"""监控自选基金限额"""

import sys
import time
sys.path.append('.')

import yaml
from src.browser_manager import BrowserManager
from src.fund_collector import FundCollector
from src.quota_analyzer import QuotaAnalyzer
from src.notifier import Notifier
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./data/logs/quota_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def fund_monitor(manager, config):
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
        report = "无大于限额的基金"
        logging.info(report)


def main():
    manager = BrowserManager()
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    gap_hour = config['schedule']['gap_hour']
    is_error = False

    while True:
        try:
            manager.start()
            # 检查登录
            if not manager.check_login_status():
                raise ValueError('未登录请重新登录')
            # 采集数据
            else:
                fund_monitor(manager, config)
        except Exception:
            import traceback
            error_msg = traceback.format_exc()
            print(error_msg)
            is_error = True
        finally:
            manager.close()

        if not is_error:
            logging.info(f'等待 {gap_hour} 小时将再次检查\n')
            time.sleep(gap_hour * 3600)
        else:
            notifier = Notifier(config)
            subject = "【错误】QDII基金限额监控"
            notifier.send(subject, "基金限额监控错误")
            print('出现错误退出监控')
            break


if __name__ == "__main__":
    main()
