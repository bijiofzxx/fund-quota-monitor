import urllib.parse
import json
import logging
from typing import List, Dict
from playwright.sync_api import Page
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
        """搜索基金并返回基金列表"""
        page = self.browser_manager.get_page()
        
        # URL编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"{self.config['eastmoney']['search_url']}?spm=search&key={encoded_keyword}#key{encoded_keyword}"
        
        self.logger.info(f"搜索关键词: {keyword}")
        page.goto(search_url, wait_until='networkidle')
        page.wait_for_timeout(2000)
        
        # 解析搜索结果
        # 需要根据实际页面结构调整选择器
        funds = []
        try:
            # 示例选择器 - 需要根据实际页面调整
            fund_rows = page.locator('.fundItem, .search-result-item, table tbody tr').all()
            
            for row in fund_rows:
                try:
                    # 提取基金代码和名称
                    code_elem = row.locator('[href*="/"]').first
                    code = code_elem.get_attribute('href').split('/')[-1].replace('.html', '')
                    name = code_elem.inner_text().strip()
                    
                    if code and name:
                        funds.append({
                            'code': code,
                            'name': name,
                            'keyword': keyword
                        })
                except Exception as e:
                    continue
            
            self.logger.info(f"找到 {len(funds)} 只符合条件的基金")
            
        except Exception as e:
            self.logger.error(f"解析搜索结果失败: {e}")
        
        return funds
    
    def add_to_favorites(self, fund_code: str, fund_name: str) -> bool:
        """将基金加入自选"""
        page = self.browser_manager.get_page()
        
        try:
            # 访问基金详情页
            detail_url = self.config['eastmoney']['detail_url'].format(code=fund_code)
            self.logger.info(f"访问基金详情: {fund_code} - {fund_name}")
            page.goto(detail_url, wait_until='networkidle')
            page.wait_for_timeout(1000)
            
            # 查找并点击"加自选"按钮
            # 需要根据实际页面调整选择器
            add_button = page.locator('text=加自选, .addOptional, #addOptional').first
            
            if add_button.is_visible():
                add_button.click()
                page.wait_for_timeout(1000)
                self.logger.info(f"✓ 已加入自选: {fund_code}")
                return True
            else:
                # 可能已经在自选中
                self.logger.info(f"基金可能已在自选中: {fund_code}")
                return True
                
        except Exception as e:
            self.logger.error(f"加入自选失败 {fund_code}: {e}")
            return False
    
    def sync_favorites(self) -> int:
        """同步所有关键词的基金到自选"""
        new_count = 0
        
        for keyword in self.config['monitor']['keywords']:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"处理关键词: {keyword}")
            self.logger.info(f"{'='*50}")
            
            funds = self.search_funds_by_keyword(keyword)
            
            for fund in funds:
                code = fund['code']
                
                # 检查是否已存在
                if code in self.existing_funds:
                    self.logger.info(f"跳过已存在的基金: {code} - {fund['name']}")
                    continue
                
                # 加入自选
                if self.add_to_favorites(code, fund['name']):
                    self.existing_funds[code] = {
                        'name': fund['name'],
                        'keyword': keyword,
                        'added_date': str(Path(__file__).stat().st_mtime)
                    }
                    new_count += 1
                    
                page.wait_for_timeout(2000)  # 避免请求过快
        
        # 保存更新
        if new_count > 0:
            self._save_master_funds()
            self.logger.info(f"\n✓ 本次新增 {new_count} 只基金到自选")
        else:
            self.logger.info("\n○ 没有新增基金")
        
        return new_count