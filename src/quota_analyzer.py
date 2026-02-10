import pandas as pd
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class QuotaAnalyzer:
    """限额分析和通知决策"""
    
    def __init__(self, config):
        self.config = config
        self.threshold = config['monitor']['quota_threshold']
        self.logger = logging.getLogger(__name__)
        
        self.state_file = Path(config['storage']['state_file'])
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.notification_state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载通知状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'last_notification': {},
            'notified_today': []
        }
    
    def _save_state(self):
        """保存通知状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.notification_state, f, ensure_ascii=False, indent=2)
    
    def analyze(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
        """
        分析限额数据
        返回: (符合条件的基金DataFrame, 是否需要通知)
        """
        if df.empty:
            return pd.DataFrame(), False
        
        # 筛选符合条件的基金
        qualified = df[(df['quota'] >= self.threshold) & (df['can_purchase'] == True)].copy()
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"限额分析结果:")
        self.logger.info(f"  阈值: {self.threshold} 元")
        self.logger.info(f"  总基金数: {len(df)}")
        self.logger.info(f"  符合条件: {len(qualified)} 只")
        self.logger.info(f"{'='*50}\n")
        
        if qualified.empty:
            return qualified, False
        
        # 判断是否需要通知
        need_notify = self._should_notify(qualified)
        
        return qualified, need_notify
    
    def _should_notify(self, qualified_df: pd.DataFrame) -> bool:
        """判断是否需要发送通知"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 检查今天是否已通知过这些基金
        current_codes = set(qualified_df['code'].tolist())
        
        # 有新的符合条件的基金
        new_funds = current_codes
        if 'last_notification' not in self.notification_state:
            self.notification_state['last_notification'] = dict()
        if 'notified_today' not in self.notification_state:
            self.notification_state['lnotified_today'] = []
        if new_funds:
            self.logger.info(f"发现 {len(new_funds)} 只新符合条件的基金")
            # 更新通知状态
            self.notification_state['notified_today'] = list(current_codes)
            self.notification_state['last_notification'][today] = {
                'funds': list(current_codes),
                'count': len(current_codes),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self._save_state()
            return True
        
        return False
    
    def reset_daily_state(self):
        """重置每日通知状态(每天首次运行时调用)"""
        self.notification_state['notified_today'] = []
        self._save_state()
        self.logger.info("已重置每日通知状态")
    
    def generate_report(self, df: pd.DataFrame) -> str:
        """生成报告文本"""
        if df.empty:
            return f"今日暂无申购限额 >= {self.threshold} 元的基金"
        
        report_lines = [
            f"📊 QDII基金限额监控报告",
            f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🎯 限额阈值: {self.threshold} 元",
            f"✅ 符合条件: {len(df)} 只基金\n",
            "=" * 60,
        ]
        
        # 按限额降序排列
        df_sorted = df.sort_values('quota', ascending=False)
        
        for idx, row in df_sorted.iterrows():
            quota_display = f"{row['quota']:.0f}元" if row['quota'] != float('inf') else "不限"
            
            report_lines.append(
                f"\n{idx+1}. {row['name']} ({row['code']})\n"
                f"   💰 申购限额: {quota_display}\n"
                f"   📈 单位净值: {row.get('nav', 'N/A')}\n"
                f"   📊 涨跌幅: {row.get('growth_rate', 'N/A')}"
            )
        
        report_lines.append("\n" + "=" * 60)
        
        return "\n".join(report_lines)