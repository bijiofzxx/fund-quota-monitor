import urllib.parse
import json
import logging
from typing import List, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pathlib import Path

class FundSearcher:
    """基金搜索和自选管理"""
    
    def __init__(self, browser_manager, config):
        self.browser_manager = browser_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.master_file = Path(config['storage']['master_file'])
        self.master_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已有基金列表
        self.existing_funds = self._load_master_funds()
    
    def _load_master_funds(self) -> Dict[str, Dict]:
        """加载已监控的基金列表"""
        if self.master_file.exists():
            with open(self.master_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_master_funds(self):
        """保存基金列表"""
        with open(self.master_file, 'w', encoding='utf-8') as f:
            json.dump(self.existing_funds, f, ensure_ascii=False, indent=2)
        self.logger.info(f"已保存 {len(self.existing_funds)} 只基金到主列表")
    
    def search_funds_by_keyword(self, keyword: str) -> List[Dict]:
        """
        搜索基金并返回基金列表
        
        步骤:
        1. 找到 id="jj" 的 div
        2. 如果存在"点击展开更多"链接，点击展开
        3. 查找包含"代码"表头的 table
        4. 提取所有基金代码和名称
        """
        page = self.browser_manager.get_page()
        
        # URL编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"{self.config['eastmoney']['search_url']}?spm=search&key={encoded_keyword}#key{encoded_keyword}"
        
        self.logger.info(f"搜索关键词: {keyword}")
        self.logger.info(f"搜索URL: {search_url}")
        
        try:
            page.goto(search_url, wait_until='networkidle', timeout=150000)

            page.wait_for_timeout(2000)
            
            # 1. 找到 id="jj" 的 div
            jj_div = page.locator('div#jj').first
            
            if not jj_div.is_visible(timeout=5000):
                self.logger.warning("未找到搜索结果区域 (id='jj')")
                return []
            
            # 2. 检查并点击"点击展开更多"
            self._expand_more_results(jj_div)
            
            # 3. 查找并解析包含"代码"的表格
            funds = self._parse_fund_tables(jj_div, keyword)
            
            self.logger.info(f"✓ 找到 {len(funds)} 只符合条件的基金")
            
            # 打印前5条结果供确认
            if funds:
                self.logger.info("前5条结果预览:")
                for i, fund in enumerate(funds[:5], 1):
                    self.logger.info(f"  {i}. {fund['code']} - {fund['name']}")
            
            return funds
            
        except Exception as e:
            self.logger.error(f"搜索失败: {e}", exc_info=True)
            return []
    
    def _expand_more_results(self, jj_div):
        """点击展开更多结果"""
        try:
            # 查找"点击展开更多"或类似文本的链接
            expand_patterns = [
                'text=点击展开更多',
                'text=展开更多',
                'text=更多',
                'a:has-text("展开")',
                'a:has-text("更多")',
            ]
            
            for pattern in expand_patterns:
                try:
                    expand_link = jj_div.locator(pattern).first
                    if expand_link.is_visible(timeout=2000):
                        self.logger.info("发现'展开更多'链接，点击展开...")
                        expand_link.click()
                        # 等待内容加载
                        jj_div.page.wait_for_timeout(2000)
                        self.logger.info("✓ 已展开全部结果")
                        return
                except PlaywrightTimeoutError:
                    continue
            
            self.logger.info("未发现'展开更多'链接，使用当前结果")
            
        except Exception as e:
            self.logger.warning(f"展开更多结果时出错: {e}")
    
    def _parse_fund_tables(self, jj_div, keyword: str) -> List[Dict]:
        """
        解析 jj_div 下的所有表格，提取包含"代码"表头的表格数据
        """
        funds = []
        
        try:
            # 获取所有 table 元素
            tables = jj_div.locator('table').all()
            self.logger.info(f"找到 {len(tables)} 个表格")
            
            for table_idx, table in enumerate(tables, 1):
                self.logger.info(f"\n分析第 {table_idx} 个表格...")
                
                # 检查表头是否包含"代码"
                if not self._has_code_header(table):
                    self.logger.info(f"  表格 {table_idx} 不包含'代码'列，跳过")
                    continue
                
                self.logger.info(f"  ✓ 表格 {table_idx} 包含'代码'列，开始提取数据")
                
                # 提取该表格的基金数据
                table_funds = self._extract_funds_from_table(table, keyword)
                funds.extend(table_funds)
                
                self.logger.info(f"  从表格 {table_idx} 提取了 {len(table_funds)} 只基金")
        
        except Exception as e:
            self.logger.error(f"解析表格失败: {e}", exc_info=True)
        
        # 去重（基于基金代码）
        unique_funds = {}
        for fund in funds:
            code = fund['code']
            if code not in unique_funds:
                unique_funds[code] = fund
        
        return list(unique_funds.values())
    
    def _has_code_header(self, table) -> bool:
        """检查表格是否包含'代码'表头"""
        try:
            # 查找 thead 或第一个 tr
            headers = table.locator('thead th, thead td, tr:first-child th, tr:first-child td').all()
            
            for header in headers:
                header_text = header.inner_text().strip()
                if '代码' in header_text:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"检查表头失败: {e}")
            return False
    
    def _extract_funds_from_table(self, table, keyword: str) -> List[Dict]:
        """从单个表格中提取基金数据"""
        funds = []
        
        try:
            # 获取表头，确定"代码"和"基金名称"的列索引
            headers = table.locator('thead th, thead td, tr:first-child th, tr:first-child td').all()
            header_texts = [h.inner_text().strip() for h in headers]
            
            # 查找列索引
            code_idx = None
            name_idx = None
            
            for idx, text in enumerate(header_texts):
                if '代码' in text:
                    code_idx = idx
                if '名称' in text or '基金名称' in text:
                    name_idx = idx
            
            if code_idx is None:
                self.logger.warning("未找到'代码'列")
                return []
            
            self.logger.info(f"  列索引 - 代码: {code_idx}, 名称: {name_idx}")
            
            # 获取数据行（跳过表头）
            # 尝试从 tbody 获取，如果没有 tbody 则从 tr 获取（跳过第一行）
            tbody = table.locator('tbody').first
            if tbody.is_visible(timeout=1000):
                rows = tbody.locator('tr').all()
            else:
                all_rows = table.locator('tr').all()
                rows = all_rows[1:] if len(all_rows) > 1 else []  # 跳过表头行
            
            self.logger.info(f"  找到 {len(rows)} 行数据")
            
            # 提取每行数据
            for row_idx, row in enumerate(rows, 1):
                try:
                    cells = row.locator('td, th').all()
                    
                    if len(cells) <= max(code_idx, name_idx or 0):
                        continue
                    
                    # 提取代码
                    code_cell = cells[code_idx]
                    code_text = code_cell.inner_text().strip()
                    
                    # 代码可能在链接中，尝试提取
                    code_link = code_cell.locator('a').first
                    if code_link.is_visible(timeout=500):
                        href = code_link.get_attribute('href') or ''
                        # 从链接中提取代码: /270042.html -> 270042
                        import re
                        match = re.search(r'/(\d+)\.html', href)
                        if match:
                            code = match.group(1)
                        else:
                            code = code_text
                    else:
                        code = code_text
                    
                    # 清理代码（移除非数字字符）
                    code = ''.join(filter(str.isdigit, code))
                    
                    if not code or len(code) != 6:  # 基金代码通常是6位数字
                        continue
                    
                    # 提取名称
                    if name_idx is not None:
                        name_cell = cells[name_idx]
                        name = name_cell.inner_text().strip()
                    else:
                        # 如果没有名称列，尝试从代码单元格的链接文本获取
                        try:
                            name = code_cell.locator('a').first.inner_text().strip()
                        except:
                            name = f"基金{code}"
                    
                    funds.append({
                        'code': code,
                        'name': name,
                        'keyword': keyword
                    })
                    
                except Exception as e:
                    self.logger.warning(f"  解析第 {row_idx} 行失败: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"提取表格数据失败: {e}", exc_info=True)
        
        return funds
    
    def add_to_favorites(self, fund_code: str, fund_name: str) -> bool:
        """将基金加入自选"""
        page = self.browser_manager.get_page()
        
        try:
            # 访问基金详情页
            detail_url = self.config['eastmoney']['detail_url'].format(code=fund_code)
            self.logger.info(f"访问基金详情: {fund_code} - {fund_name}")
            page.goto(detail_url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(2000)
            
            # 查找并点击"加自选"按钮
            # 可能的选择器
            add_button_selectors = [
                'text=加自选',
                '.addOptional',
                '#addOptional',
                'a:has-text("加自选")',
                'button:has-text("加自选")',
                'span:has-text("加自选")',
            ]
            
            button_found = False
            for selector in add_button_selectors:
                try:
                    add_button = page.locator(selector).first
                    if add_button.is_visible(timeout=2000):
                        add_button.click()
                        page.wait_for_timeout(1500)
                        self.logger.info(f"✓ 已加入自选: {fund_code}")
                        button_found = True
                        break
                except PlaywrightTimeoutError:
                    continue
            
            if not button_found:
                # 可能已经在自选中
                # 检查是否有"已添加"或"取消自选"等文本
                if page.locator('text=取消自选, text=已添加').first.is_visible(timeout=2000):
                    self.logger.info(f"基金已在自选中: {fund_code}")
                    return True
                else:
                    self.logger.warning(f"未找到'加自选'按钮: {fund_code}")
                    return False
            
            return True
                
        except Exception as e:
            self.logger.error(f"加入自选失败 {fund_code}: {e}")
            return False
    
    def sync_favorites(self) -> int:
        """同步所有关键词的基金到自选"""
        new_count = 0
        
        for keyword in self.config['monitor']['keywords']:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"处理关键词: {keyword}")
            self.logger.info(f"{'='*60}")
            
            funds = self.search_funds_by_keyword(keyword)
            
            if not funds:
                self.logger.warning(f"关键词 '{keyword}' 未找到任何基金")
                continue
            
            for fund in funds:
                code = fund['code']
                
                # 检查是否已存在
                if code in self.existing_funds:
                    self.logger.info(f"跳过已存在的基金: {code} - {fund['name']}")
                    continue
                
                # 加入自选
                if self.add_to_favorites(code, fund['name']):
                    from datetime import datetime
                    self.existing_funds[code] = {
                        'name': fund['name'],
                        'keyword': keyword,
                        'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    new_count += 1
                
                # 避免请求过快
                page = self.browser_manager.get_page()
                page.wait_for_timeout(2000)
        
        # 保存更新
        if new_count > 0:
            self._save_master_funds()
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"✓ 本次新增 {new_count} 只基金到自选")
            self.logger.info(f"{'='*60}\n")
        else:
            self.logger.info(f"\n{'='*60}")
            self.logger.info("○ 没有新增基金")
            self.logger.info(f"{'='*60}\n")
        
        return new_count