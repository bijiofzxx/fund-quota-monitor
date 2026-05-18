#!/usr/bin/env python3
"""基金信息采集器"""

import pandas as pd
import re
from typing import Dict, Optional, List
from src.browser_manager import BrowserManager


def get_fund_info(manager: BrowserManager, code: str) -> Dict[str, str]:
    """
    获取基金的详细信息

    Args:
        manager: 浏览器管理器
        code: 基金代码

    Returns:
        Dict: 包含基金详细信息的字典，获取失败的字段值为"-"
    """
    fund_info = {
        'code': code,
        'nav': '-',  # 单位净值
        'accumulated_nav': '-',  # 累计净值
        '1_month': '-',  # 近1月
        '3_month': '-',  # 近3月
        '6_month': '-',  # 近6月
        '1_year': '-',  # 近1年
        '3_year': '-',  # 近3年
        'since_inception': '-',  # 成立以来
        'scale': '-',  # 规模
        'establish_date': '-',  # 成立日
        'benchmark': '-',  # 跟踪标的
        'tracking_error': '-',  # 跟踪误差
        'annual_tracking_error': '-',  # 年化跟踪误差
        'purchase_fee': '-',  # 购买手续费
        'management_fee': '-',  # 管理费
        'custody_fee': '-'  # 托管费
    }

    try:
        # 确保浏览器已启动
        if not manager.context:
            manager.start()

        # 获取或创建页面
        page = manager.get_page()

        # 导航到基金详情页
        url = f"https://fund.eastmoney.com/{code}.html"
        page.goto(url, wait_until='networkidle', timeout=30 * 1000)

        # 等待页面加载完成
        page.wait_for_load_state('networkidle')

        # 获取页面内容
        page_content = page.content()

        # 1. 获取净值信息
        try:
            nav_pattern = r'单位净值[：:\s]*([\d.]+)'
            accumulated_pattern = r'累计净值[：:\s]*([\d.]+)'

            nav_match = re.search(nav_pattern, page_content)
            if nav_match:
                fund_info['nav'] = nav_match.group(1)

            accumulated_match = re.search(accumulated_pattern, page_content)
            if accumulated_match:
                fund_info['accumulated_nav'] = accumulated_match.group(1)
        except:
            pass

        # 2. 获取收益率信息
        try:
            performance_patterns = {
                '近1月': r'近1月[：:\s]*(-?[\d.]+)%',
                '近3月': r'近3月[：:\s]*(-?[\d.]+)%',
                '近6月': r'近6月[：:\s]*(-?[\d.]+)%',
                '近1年': r'近1年[：:\s]*(-?[\d.]+)%',
                '近3年': r'近3年[：:\s]*(-?[\d.]+)%',
                '成立以来': r'成立以来[：:\s]*(-?[\d.]+)%'
            }

            for key, pattern in performance_patterns.items():
                match = re.search(pattern, page_content)
                if match:
                    fund_info[key.lower().replace('近', '').replace('以来', 'since_inception').replace('年', '_year').replace('月', '_month')] = match.group(1) + "%"
        except:
            pass

        # 3. 获取规模和成立日
        try:
            scale_pattern = r'基金规模[：:\s]*([\d.]+)([亿千万])'
            date_pattern = r'成立日期[：:\s]*(\d{4}-\d{2}-\d{2})'

            scale_match = re.search(scale_pattern, page_content)
            if scale_match:
                value = float(scale_match.group(1))
                unit = scale_match.group(2)
                if unit == '亿':
                    fund_info['scale'] = f"{value}亿"
                elif unit == '千万':
                    fund_info['scale'] = f"{value}千万"

            date_match = re.search(date_pattern, page_content)
            if date_match:
                fund_info['establish_date'] = date_match.group(1)
        except:
            pass

        # 4. 获取跟踪标的和误差
        try:
            benchmark_pattern = r'跟踪标的[：:\s]*(.+?)(?=，|。|$)'
            tracking_error_pattern = r'跟踪误差[：:\s]*([\d.]+)%'
            annual_error_pattern = r'年化跟踪误差[：:\s]*([\d.]+)%'

            benchmark_match = re.search(benchmark_pattern, page_content)
            if benchmark_match:
                fund_info['benchmark'] = benchmark_match.group(1).strip()

            tracking_match = re.search(tracking_error_pattern, page_content)
            if tracking_match:
                fund_info['tracking_error'] = tracking_match.group(1) + "%"

            annual_match = re.search(annual_error_pattern, page_content)
            if annual_match:
                fund_info['annual_tracking_error'] = annual_match.group(1) + "%"
        except:
            pass

        # 5. 获取费率信息
        try:
            fee_patterns = {
                'purchase_fee': r'购买手续费[：:\s]*([\d.]+)%',
                'management_fee': r'管理费[：:\s]*([\d.]+)%',
                'custody_fee': r'托管费[：:\s]*([\d.]+)%'
            }

            for key, pattern in fee_patterns.items():
                match = re.search(pattern, page_content)
                if match:
                    fund_info[key] = match.group(1) + "%"
        except:
            pass

    except Exception as e:
        print(f"获取基金信息时出错: {e}")

    return fund_info


def get_tracking_error(manager: BrowserManager, code: str) -> str:
    """
    获取基金的跟踪误差值（保留向后兼容）

    Args:
        manager: 浏览器管理器
        code: 基金代码

    Returns:
        str: 跟踪误差值，如果没有找到或出错返回"-"
    """
    fund_info = get_fund_info(manager, code)
    return fund_info.get('tracking_error', '-')