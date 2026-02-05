import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict
from playwright.sync_api import Page

class FundCollector:
    """自选基金数据采集"""
    
    def __init__(self, browser_manager, config):
        self.browser_manager = browser_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.history_dir = Path(config['storage']['quota_history_dir'])
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_quota_data(self) -> pd.DataFrame:
        """从自选基金页面采集限额数据"""
        page = self.browser_manager.get_page()
        
        self.logger.info("开始采集自选基金限额数据...")
        page.goto(self.config['eastmoney']['favorite_url'], wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        funds_data = []
        
        try:
            # 需要根据实际页面结构调整选择器
            # 这里假设自选基金以表格形式展示
            fund_rows = page.locator('table tbody tr, .fund-item').all()
            
            self.logger.info(f"找到 {len(fund_rows)} 只自选基金")
            
            for row in fund_rows:
                try:
                    data = self._parse_fund_row(row)
                    if data:
                        funds_data.append(data)
                except Exception as e:
                    self.logger.warning(f"解析基金行失败: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"采集数据失败: {e}")
            return pd.DataFrame()
        
        if not funds_data:
            self.logger.warning("未采集到任何数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(funds_data)
        
        # 保存到CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = self.history_dir / f"quota_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        self.logger.info(f"✓ 已保存数据到: {csv_path}")
        self.logger.info(f"✓ 共采集 {len(df)} 只基金数据")
        
        return df
    
    def _parse_fund_row(self, row) -> Dict:
        """解析单行基金数据"""
        # 需要根据实际页面结构调整
        # 以下是示例代码
        
        try:
            code = row.locator('.fund-code, [data-code]').first.inner_text().strip()
            name = row.locator('.fund-name').first.inner_text().strip()
            
            # 申购限额可能在不同位置
            quota_text = row.locator('.quota, .purchase-limit').first.inner_text().strip()
            quota = self._parse_quota_value(quota_text)
            
            # 其他有用信息
            nav = row.locator('.nav, .net-value').first.inner_text().strip()
            growth_rate = row.locator('.growth-rate, .rate').first.inner_text().strip()
            
            return {
                'code': code,
                'name': name,
                'quota': quota,
                'quota_text': quota_text,
                'nav': nav,
                'growth_rate': growth_rate,
                'collect_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            raise ValueError(f"解析失败: {e}")
    
    def _parse_quota_value(self, quota_text: str) -> float:
        """解析限额文本为数值"""
        # 处理各种格式: "1000元", "不限", "1万元", "暂停申购"
        
        if not quota_text or quota_text in ['不限', '无限制']:
            return float('inf')
        
        if '暂停' in quota_text or '关闭' in quota_text:
            return 0.0
        
        # 提取数字
        import re
        numbers = re.findall(r'[\d.]+', quota_text)
        
        if not numbers:
            return 0.0
        
        value = float(numbers[0])
        
        # 处理单位
        if '万' in quota_text:
            value *= 10000
        elif '千' in quota_text:
            value *= 1000
        
        return value
    
    def get_latest_data(self) -> pd.DataFrame:
        """获取最新的限额数据"""
        csv_files = sorted(self.history_dir.glob('quota_*.csv'), reverse=True)
        
        if not csv_files:
            self.logger.warning("没有历史数据")
            return pd.DataFrame()
        
        latest_file = csv_files[0]
        self.logger.info(f"读取最新数据: {latest_file.name}")
        
        return pd.read_csv(latest_file, encoding='utf-8-sig')