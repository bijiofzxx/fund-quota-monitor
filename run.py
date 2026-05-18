#!/usr/bin/env python3
"""主程序 - 完整的调度系统"""

import schedule
import os
import time
import yaml
import logging
from pathlib import Path
import subprocess
from datetime import datetime

# 配置日志
log_dir = Path('./data/logs')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_script(script_path: str, description: str, python_interpreter: str):
    """运行Python脚本"""
    logger.info(f"{'='*60}")
    logger.info(f"执行任务: {description}")
    logger.info(f"{'='*60}")
    
    
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        result = subprocess.run([python_interpreter, script_path],
                                capture_output=True, text=True,
                                encoding='utf-8', env=env)
        
        if result.returncode == 0:
            logger.info(f"✓ {description} 完成")
        else:
            logger.error(f"✗ {description} 失败:\n{result.stderr}")
            
    except Exception as e:
        logger.error(f"✗ {description} 异常: {e}")

def daily_search_task(python_interpreter: str):
    """每日搜索任务"""
    run_script('scripts/daily_search.py', '基金搜索', python_interpreter=python_interpreter)

def quota_check_task(python_interpreter: str):
    """限额检查任务"""
    run_script('scripts/quota_monitor.py', '限额监控', python_interpreter=python_interpreter)

def main():
    # 加载配置
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    schedule_config = config['schedule']
    python_interpreter = config['python_interpreter']
    
    # 自选基金改为手动 python scripts/daily_search.py
    # # 配置定时任务
    # schedule.every().day.at(schedule_config['search_funds']).do(daily_search_task, python_interpreter=python_interpreter)
    
    for check_time in schedule_config['check_quota']:
        schedule.every().day.at(check_time).do(quota_check_task, python_interpreter=python_interpreter)
    
    logger.info("\n" + "="*60)
    logger.info("QDII基金限额监控系统已启动")
    logger.info("="*60)
    # logger.info(f"每日搜索时间: {schedule_config['search_funds']}")
    logger.info("="*60 + "\n")
    
    # 启动时立即执行一次检查
    logger.info("启动计划任务前,执行一次任务测试...")
    quota_check_task(python_interpreter=python_interpreter)
    logger.info("任务测试成功,启动计划任务")
    logger.info(f"计划任务时间: {', '.join(schedule_config['check_quota'])}")
    logger.info("请勿关闭程序")
  
    # 进入调度循环
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n程序已停止")