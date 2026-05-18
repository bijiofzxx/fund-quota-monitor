#!/usr/bin/env python3
"""监控自选基金限额"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import os
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
    report_data = analyzer.generate_report(qualified_df, manager)

    # 打印HTML报告（简化版本）
    print(f"\n{'='*60}")
    print(f"📊 QDII基金限额监控报告")
    print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 限额阈值: {config['monitor']['quota_threshold']} 元")
    print(f"✅ 符合条件: {len(qualified_df)} 只基金")
    print(f"{'='*60}\n")

    # 保存HTML和CSV文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_file = f"./data/reports/fund_quota_report_{timestamp}.html"
    csv_file = f"./data/reports/fund_quota_data_{timestamp}.csv"

    # 创建报告目录
    os.makedirs("./data/reports", exist_ok=True)

    # 保存HTML文件
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(report_data['html'])

    # 保存CSV文件
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write(report_data['csv'])

    print(f"📄 HTML报告已保存: {html_file}")
    print(f"📊 CSV数据已保存: {csv_file}")


    # 发送通知
    if need_notify:
        notifier = Notifier(config)
        subject = f"QDII基金限额提醒 - {len(qualified_df)}只基金符合条件"

        # 构建邮件内容（包含HTML和CSV附件）
        email_content = report_data['html']

        # 添加附件
        attachments = [html_file, csv_file]

        notifier.send(subject, email_content, attachments)
    else:
        report = "无大于限额的基金"
        logging.info(report)


def run_quota_monitor():
    manager = BrowserManager()
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    is_error = False

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
        logging.info(f'基金检查成功\n')
    else:
        notifier = Notifier(config)
        subject = "【错误】QDII基金限额监控"
        notifier.send(subject, "基金限额监控错误")
        print('出现错误退出监控')


if __name__ == "__main__":
    run_quota_monitor()
