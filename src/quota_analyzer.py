import pandas as pd
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
from src.fund_info_collector import get_fund_info

import pandas as pd
from datetime import datetime


def generate_html_report(df: pd.DataFrame) -> str:
    """
    生成HTML格式的基金监控报告。
    DataFrame 必须包含以下列：
    code, name, nav, nav_date, cumulative_nav, daily_growth_value,
    daily_growth_rate, since_inception, quota, quota_text,
    purchase_status, can_purchase, collect_time
    """

    # 列定义：(字段名, 表头显示, 对齐方式)
    COLUMNS = [
        ('code',              '基金代码',     'center'),
        ('name',              '基金名称',     'left'),
        ('quota_text',        '申购限额',     'center'),
        ('purchase_status',   '申购状态',     'center'),
        ('nav',               '单位净值',     'center'),
        ('nav_date',          '净值日期',     'center'),
        ('cumulative_nav',    '累计净值',     'center'),
        ('daily_growth_rate', '日涨跌幅',     'center'),
        ('since_inception',   '成立以来',     'center'),
    ]

    def purchase_badge(row):
        status = str(row.get('purchase_status', '-'))
        can = row.get('can_purchase', False)
        if can:
            return f'<span class="badge badge-open">{status}</span>'
        elif status in ('暂停申购', '场内交易'):
            return f'<span class="badge badge-closed">{status}</span>'
        else:
            return f'<span class="badge badge-limit">{status}</span>'

    def quota_cell(row):
        quota = row.get('quota', None)
        text = str(row.get('quota_text', '-'))
        try:
            q = float(quota)
            if q > 0:
                return f'<span class="quota-red">{text}</span>'
        except Exception:
            pass
        return f'<span class="neutral">{text}</span>'

    def growth_cell(val):
        s = str(val).replace('%', '').strip()
        try:
            v = float(s)
            cls = 'pos' if v > 0 else 'neg' if v < 0 else 'neutral'
            sign = '+' if v > 0 else ''
            return f'<span class="{cls}">{sign}{val}</span>'
        except Exception:
            return f'<span class="neutral">{val}</span>'

    def render_cell(col, row):
        if col == 'quota_text':
            return quota_cell(row)
        if col == 'purchase_status':
            return purchase_badge(row)
        if col == 'daily_growth_rate':
            return growth_cell(row.get(col, '-'))
        val = row.get(col, '-')
        return '-' if (val is None or str(val).strip() == '') else str(val)

    # 构建表头
    thead = ''.join(
        f'<th style="text-align:{align}">{label}</th>'
        for _, label, align in COLUMNS
    )

    # 构建表体
    tbody = ''
    for i, (_, row) in enumerate(df.iterrows(), 1):
        can = row.get('can_purchase', False)
        row_cls = 'row-active' if can else ''
        code = str(row.get('code', '')).strip()
        url = f'https://fund.eastmoney.com/{code}.html'
        cells = ''.join(
            f'<td style="text-align:{align}">{render_cell(col, row)}</td>'
            for col, _, align in COLUMNS
        )
        tbody += (
            f'<tr class="{row_cls}" onclick="window.open(\'{url}\',\'_blank\')" '
            f'style="cursor:pointer" title="点击查看 {code} 详情">{cells}</tr>\n'
        )

    collect_time = df['collect_time'].iloc[0] if 'collect_time' in df.columns else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = len(df)
    purchasable = int(df['can_purchase'].sum()) if 'can_purchase' in df.columns else 0

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QDII基金限额监控</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
    background: #f4f6f9;
    color: #222;
    padding: 24px 16px;
    font-size: 13px;
  }}
  .card {{
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 16px rgba(0,0,0,.08);
    overflow: hidden;
    max-width: 1100px;
    margin: 0 auto;
  }}
  .header {{
    background: linear-gradient(90deg, #1a3560 0%, #2a6dd9 100%);
    padding: 22px 28px;
    color: #fff;
  }}
  .header h1 {{ font-size: 18px; font-weight: 700; margin-bottom: 4px; }}
  .header p  {{ font-size: 12px; opacity: .75; }}
  .meta {{
    display: flex; gap: 12px; flex-wrap: wrap;
    padding: 14px 28px;
    background: #f8fafc;
    border-bottom: 1px solid #e4e8ef;
  }}
  .meta-item {{
    background: #fff;
    border: 1px solid #dde3ec;
    border-radius: 6px;
    padding: 8px 16px;
    min-width: 130px;
  }}
  .meta-item .lbl {{ font-size: 11px; color: #888; margin-bottom: 3px; }}
  .meta-item .val {{ font-size: 16px; font-weight: 700; color: #1a3560; }}
  /* 关键：表格区域双向滚动 */
  .table-wrap {{
    overflow: auto;           /* 横向 + 纵向滚动 */
    max-height: 480px;        /* 超过此高度出现纵向滚动条 */
    padding: 0;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    white-space: nowrap;
    font-size: 12.5px;
  }}
  thead th {{
    position: sticky;
    top: 0;
    z-index: 2;
    background: #1a3560;
    color: #fff;
    padding: 10px 14px;
    font-weight: 600;
    border-right: 1px solid #2a4a80;
  }}
  tbody td {{
    padding: 9px 14px;
    border-bottom: 1px solid #edf0f5;
    border-right: 1px solid #f0f2f6;
  }}
  tbody tr:hover {{ background: #eef4ff; box-shadow: inset 3px 0 0 #2a6dd9; }}
  .row-active {{ background: #f0fdf4; }}

  /* 颜色语义 */
  .pos     {{ color: #16a34a; font-weight: 600; }}
  .neg     {{ color: #dc2626; font-weight: 600; }}
  .neutral {{ color: #aaa; }}
  .quota-red {{ color: #dc2626; font-weight: 700; }}

  /* 徽章 */
  .badge {{
    display: inline-block; padding: 2px 9px; border-radius: 99px;
    font-size: 11px; font-weight: 600;
  }}
  .badge-open   {{ background: #dcfce7; color: #15803d; }}
  .badge-closed {{ background: #f1f5f9; color: #94a3b8; }}
  .badge-limit  {{ background: #fee2e2; color: #b91c1c; }}

  .footer {{
    text-align: center; padding: 12px;
    font-size: 11px; color: #aaa;
    border-top: 1px solid #eee;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>📊 QDII 基金限额监控报告</h1>
    <p>数据采集时间：{collect_time}</p>
  </div>
  <div class="meta">
    <div class="meta-item"><div class="lbl">符合申购条件数</div><div class="val" style="color:#16a34a">{purchasable} 只</div></div>
    <div class="meta-item"><div class="lbl">报告生成时间</div><div class="val" style="font-size:13px">{datetime.now().strftime('%H:%M:%S')}</div></div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr>{thead}</tr></thead>
      <tbody>{tbody}</tbody>
    </table>
  </div>
  <div class="footer">数据仅供参考，不构成投资建议 · © QDII基金限额监控系统</div>
</div>
</body>
</html>"""
    return html


def generate_csv_data(df: pd.DataFrame) -> str:
    """
    生成CSV附件内容（UTF-8 BOM，Excel可直接打开）。
    返回字符串，调用方可用 .encode('utf-8-sig') 写入文件或附件。
    """
    col_map = {
        'code':              '基金代码',
        'name':              '基金名称',
        'quota':             '申购限额(元)',
        'quota_text':        '限额说明',
        'purchase_status':   '申购状态',
        'can_purchase':      '可申购',
        'nav':               '单位净值',
        'nav_date':          '净值日期',
        'cumulative_nav':    '累计净值',
        'daily_growth_value':'日涨跌额',
        'daily_growth_rate': '日涨跌幅',
        'since_inception':   '成立以来',
        'collect_time':      '采集时间',
    }
 
    out_cols = [c for c in col_map if c in df.columns]
    header = ','.join(col_map[c] for c in out_cols)
 
    def escape(val):
        s = str(val) if val is not None else ''
        if any(ch in s for ch in [',', '"', '\n']):
            s = '"' + s.replace('"', '""') + '"'
        return s
 
    lines = ['\ufeff' + header]  # BOM for Excel
    for _, row in df.iterrows():
        lines.append(','.join(escape(row.get(c, '')) for c in out_cols))
 
    return '\n'.join(lines)


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
    
    def generate_report(self, df: pd.DataFrame, manager=None) -> Dict[str, str]:
        """生成HTML报告和CSV数据"""
        if df.empty:
            return {
                'html': f"<p>今日暂无申购限额 >= {self.threshold} 元的基金</p>",
                'csv': "今日暂无申购限额 >= {self.threshold} 元的基金"
            }

        # 确保数据已加载基金详细信息
        if manager is not None:
            for idx, row in df.iterrows():
                if 'code' in row:
                    fund_info = get_fund_info(manager, row['code'])
                    # 将基金信息合并到DataFrame中
                    for key, value in fund_info.items():
                        if key not in df.columns:
                            df[key] = '-'
                    df.loc[idx, list(fund_info.keys())] = list(fund_info.values())

        # 按限额降序排列
        df_sorted = df.sort_values('quota', ascending=False)
    
        html_content = generate_html_report(df_sorted)
        csv_content = generate_csv_data(df_sorted)

        return {
            'html': html_content,
            'csv': csv_content
        }
