import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
import re
from typing import List, Dict, Tuple
from playwright.sync_api import Page, Locator

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
        page.goto(self.config['eastmoney']['favorite_url'], wait_until='networkidle', timeout=10 * 30000)
        page.wait_for_timeout(3000)
        
        all_funds_data = []
        
        try:
            # 查找所有基金分组的表格
            # 根据HTML结构，表格的class为 "em-table em-table-multi em-table-check js-fundlist-table"
            table = page.locator('table.em-table.js-fundlist-table[data-type="hk"]').first
            
            self.logger.info(f"找到基金分组表格")
            
            # 获取该表格所有基金行
            # 基金行的class包含 "fund-row"
            fund_rows = table.locator('tbody tr.fund-row').all()
            
            self.logger.info(f"  表格包含 {len(fund_rows)} 只基金")
            
            for row_idx, row in enumerate(fund_rows, 1):
                try:
                    fund_data = self._parse_fund_row(row)
                    if fund_data:
                        all_funds_data.append(fund_data)
                        
                        # 每10只基金输出一次进度
                        if row_idx % 10 == 0:
                            self.logger.info(f"  已处理 {row_idx}/{len(fund_rows)} 只基金...")
                except Exception as e:
                    self.logger.warning(f"  解析第 {row_idx} 只基金失败: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"采集数据失败: {e}", exc_info=True)
            return pd.DataFrame()
        
        if not all_funds_data:
            self.logger.warning("未采集到任何数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_funds_data)
        
        # 保存到CSV - 使用正确的格式 %Y%m%d_%H%M%S
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = self.history_dir / f"quota_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"✓ 数据采集完成!")
        self.logger.info(f"  保存路径: {csv_path}")
        self.logger.info(f"  基金总数: {len(df)}")
        self.logger.info(f"  可申购: {df['can_purchase'].sum()} 只")
        self.logger.info(f"  暂停申购: {(~df['can_purchase']).sum()} 只")
        self.logger.info(f"{'='*60}\n")
        
        return df
    
    def _parse_fund_row(self, row: Locator) -> Dict:
        """
        解析单行基金数据
        
        HTML结构分析:
        - 基金代码: data-fundcode 属性
        - 基金名称: data-fundname 属性
        - 单位净值: td.rq.js-dwjz > p.jz
        - 累计净值: 第4个td
        - 日增长值: 第5个td
        - 日增长率: 第6个td (class包含js-rzdf)
        - 成立来: 第7个td
        - 单日申购限额: 第8个td (class="zt js-rzdf>")
        - 申购状态: 第9个td (class="zt")
        - 购买按钮: td.cz > a.em-button (检查是否包含em-button-disable)
        """
        try:
            # 1. 基金代码和名称 - 从tr的data属性获取
            code = row.get_attribute('data-fundcode')
            name = row.get_attribute('data-fundname')
            
            if not code:
                raise ValueError("未找到基金代码")
            
            # 2. 获取所有td单元格
            cells = row.locator('td').all()
            
            # 3. 单位净值 (第3个td, class="rq js-dwjz")
            nav_cell = cells[2] if len(cells) > 2 else None
            if nav_cell:
                nav_text = nav_cell.locator('p.jz').first.inner_text().strip()
                nav_date = nav_cell.locator('p.rq').first.inner_text().strip()
            else:
                nav_text = ''
                nav_date = ''
            
            # 4. 累计净值 (第4个td)
            cumulative_nav = cells[3].inner_text().strip() if len(cells) > 3 else ''
            
            # 5. 日增长值 (第5个td)
            daily_growth_value = cells[4].inner_text().strip() if len(cells) > 4 else ''
            
            # 6. 日增长率 (第6个td, class包含js-rzdf)
            daily_growth_rate = cells[5].inner_text().strip() if len(cells) > 5 else ''
            
            # 7. 成立来 (第7个td)
            since_inception = cells[6].inner_text().strip() if len(cells) > 6 else ''
            
            # 8. 单日申购限额 (第8个td, class="zt js-rzdf>")
            quota_cell = cells[7] if len(cells) > 7 else None
            if quota_cell:
                quota_text = quota_cell.inner_text().strip()
                quota_value = self._parse_quota_value(quota_text)
            else:
                quota_text = ''
                quota_value = 0.0
            
            # 9. 申购状态 (第9个td, class="zt")
            purchase_status = cells[8].inner_text().strip() if len(cells) > 8 else ''
            
            # 10. 购买按钮状态 (第10个td, class="cz")
            # 检查购买按钮是否包含 em-button-disable class
            can_purchase = False
            if len(cells) > 9:
                purchase_button = cells[9].locator('a.em-button').first
                button_class = purchase_button.get_attribute('class') or ''
                
                # 如果包含 em-button-disable，则不可购买
                can_purchase = 'em-button-disable' not in button_class
            
            return {
                'code': code,
                'name': name,
                'nav': nav_text,
                'nav_date': nav_date,
                'cumulative_nav': cumulative_nav,
                'daily_growth_value': daily_growth_value,
                'daily_growth_rate': daily_growth_rate,
                'since_inception': since_inception,
                'quota': quota_value,
                'quota_text': quota_text,
                'purchase_status': purchase_status,
                'can_purchase': can_purchase,
                'collect_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            raise ValueError(f"解析失败: {e}")
    
    def _parse_quota_value(self, quota_text: str) -> float:
        """
        解析限额文本为数值
        
        处理各种格式:
        - 空字符串或"--" -> 0.0 (无法申购或无限额信息)
        - "0元" -> 0.0
        - "100元" -> 100.0
        - "50元" -> 50.0
        - "1万元" -> 10000.0
        - "5千元" -> 5000.0
        - "不限" 或 "无限制" -> float('inf')
        - "暂停申购" -> 0.0
        """
        
        # 处理空值和特殊标记
        if not quota_text or quota_text.strip() in ['', '--', 'None']:
            return 0.0
        
        quota_text = quota_text.strip()
        
        # 处理"不限"、"无限制"
        if quota_text in ['不限', '无限制', '开放']:
            return float('inf')
        
        # 处理"暂停申购"、"关闭申购"等
        if any(keyword in quota_text for keyword in ['暂停', '关闭', '停止']):
            return 0.0
        
        # 提取数字
        numbers = re.findall(r'[\d.]+', quota_text)
        
        if not numbers:
            # 没有找到数字，返回0
            return 0.0
        
        try:
            value = float(numbers[0])
        except ValueError:
            return 0.0
        
        # 处理单位
        if '万' in quota_text:
            value *= 10000
        elif '千' in quota_text:
            value *= 1000
        elif '亿' in quota_text:
            value *= 100000000
        # 默认单位是元，不需要转换
        
        return value
    
    def get_latest_data(self) -> pd.DataFrame:
        """获取最新的限额数据"""
        csv_files = sorted(self.history_dir.glob('quota_*.csv'), reverse=True)
        
        if not csv_files:
            self.logger.warning("没有历史数据")
            return pd.DataFrame()
        
        latest_file = csv_files[0]
        self.logger.info(f"读取最新数据: {latest_file.name}")
        
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        
        # 确保can_purchase列是布尔类型
        if 'can_purchase' in df.columns:
            df['can_purchase'] = df['can_purchase'].astype(bool)
        
        return df
    
    def get_qualified_funds(self, threshold: float = None) -> pd.DataFrame:
        """
        获取符合条件的基金
        
        条件:
        1. 单日申购限额 >= 阈值
        2. 可以购买 (can_purchase == True)
        
        Args:
            threshold: 限额阈值，如果为None则从配置读取
        
        Returns:
            符合条件的基金DataFrame
        """
        if threshold is None:
            threshold = self.config['monitor']['quota_threshold']
        
        df = self.get_latest_data()
        
        if df.empty:
            self.logger.warning("没有数据可供筛选")
            return pd.DataFrame()
        
        # 筛选条件:
        # 1. quota >= threshold
        # 2. can_purchase == True
        qualified = df[
            (df['quota'] >= threshold) & 
            (df['can_purchase'] == True)
        ].copy()
        
        # 按限额降序排列
        qualified = qualified.sort_values('quota', ascending=False)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"符合条件的基金筛选:")
        self.logger.info(f"  限额阈值: {threshold} 元")
        self.logger.info(f"  总基金数: {len(df)}")
        self.logger.info(f"  限额>=阈值: {(df['quota'] >= threshold).sum()} 只")
        self.logger.info(f"  可申购: {df['can_purchase'].sum()} 只")
        self.logger.info(f"  符合条件: {len(qualified)} 只")
        self.logger.info(f"{'='*60}\n")
        
        return qualified
    
    def print_data_summary(self):
        """打印数据采集汇总信息"""
        csv_files = sorted(self.history_dir.glob('quota_*.csv'))
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"历史数据文件汇总:")
        self.logger.info(f"  数据目录: {self.history_dir}")
        self.logger.info(f"  文件总数: {len(csv_files)}")
        
        if csv_files:
            self.logger.info(f"\n最近5次采集:")
            for csv_file in csv_files[-5:]:
                file_stat = csv_file.stat()
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                # 读取文件获取基金数量
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8-sig')
                    fund_count = len(df)
                    can_purchase_count = df['can_purchase'].sum() if 'can_purchase' in df.columns else 0
                except:
                    fund_count = 0
                    can_purchase_count = 0
                
                self.logger.info(
                    f"  {csv_file.name}: {fund_count}只基金, "
                    f"{can_purchase_count}只可购, "
                    f"时间: {file_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        
        self.logger.info(f"{'='*60}\n")