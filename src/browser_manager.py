from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
import yaml
import logging
from pathlib import Path

class BrowserManager:
    """Playwright浏览器管理器 - 支持持久化上下文"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.browser_config = self.config['browser']
        self.user_data_dir = Path(self.browser_config['user_data_dir'])
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.playwright = None
        self.browser = None
        self.context = None
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> BrowserContext:
        """启动持久化浏览器上下文"""
        self.logger.info("启动Playwright浏览器...")
        
        self.playwright = sync_playwright().start()
        
        # 使用持久化上下文 - 保持登录状态
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.browser_config['headless'],
            viewport={
                'width': self.browser_config['viewport']['width'],
                'height': self.browser_config['viewport']['height']
            },
            # 反反爬设置
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        
        self.logger.info("浏览器启动成功")
        return self.context
    
    def get_page(self) -> Page:
        """获取或创建页面"""
        if not self.context:
            self.start()
        
        pages = self.context.pages
        if pages:
            return pages[0]
        else:
            return self.context.new_page()
    
    def close(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        self.logger.info("浏览器已关闭")
    
    def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            page = self.get_page()
            page.goto(self.config['eastmoney']['favorite_url'], timeout=10000)
            page.wait_for_timeout(2000)

            # 检查是否存在登录按钮或用户信息
            # 需要根据实际页面调整选择器
            is_login_text = self.config['is_login_text']
            is_logged_in = page.locator(f'text={is_login_text}').is_visible(timeout=3000)
            
            self.logger.info(f"登录状态检查: {'已登录' if is_logged_in else '未登录'}")
            return is_logged_in
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {e}")
            return False
    
    def wait_for_manual_login(self, timeout: int = 300000):
        """等待用户手动登录"""
        self.logger.info("=" * 50)
        self.logger.info("请在浏览器中完成登录操作...")
        self.logger.info("支持扫码登录或短信验证码登录")
        self.logger.info("登录完成后脚本将自动继续")
        self.logger.info("=" * 50)
        
        page = self.get_page()
        page.goto(self.config['eastmoney']['favorite_url'])
        
        try:
            # 等待登录成功的标志元素出现
            is_login_text = self.config['is_login_text']
            
            page.wait_for_selector(f'text={is_login_text}', timeout=timeout)
            self.logger.info("✓ 登录成功!")
            return True
        except Exception as e:
            self.logger.error(f"登录超时或失败: {e}")
            return False