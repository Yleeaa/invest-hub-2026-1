# -*- coding: utf-8 -*-
"""
每日抓取纳斯达克相关 QDII 基金的申购状态 / 限购额度，
生成 data.json 供网站前端读取。
数据源：天天基金（东方财富），通过 akshare 免费获取。
"""
import json
from datetime import datetime, timezone, timedelta

import akshare as ak

# 想跟踪的基金：名称里包含以下任一关键词即会被收录
KEYWORDS = ["纳斯达克"]

# 名称含以下关键词的直接排除（美元现汇/现钞份额等）
EXCLUDE_KEYWORDS = ["美元"]

# 非 A 类份额的后缀字母（C/E/I/D/B 类都排除，只留 A 类或无字母后缀的）
NON_A_SUFFIXES = ("B", "C", "D", "E", "I")

# 若想精确指定基金，可改为按代码筛选，例如：
# FUND_CODES = ["015299", "016452", "161130", "270042"]
FUND_CODES = []


def is_target_fund(name):
    """只保留：场外、人民币、A类（或无份额后缀）的基金"""
    if any(k in name for k in EXCLUDE_KEYWORDS):
        return False
    # 排除场内 ETF 本体（名字带 ETF 但不是联接基金的）
    if "ETF" in name and "联接" not in name:
        return False
    # 排除非 A 类份额（名称以 C/E/I 等字母结尾的）
    if name.strip()[-1] in NON_A_SUFFIXES:
        return False
    return True


def fetch_funds():
    """获取全部开放式基金申购状态，并按关键词/代码筛选"""
    try:
        df = ak.fund_purchase_em()
    except AttributeError:
        df = ak.fund_em_purchase()  # 兼容旧版 akshare

    if FUND_CODES:
        df = df[df["基金代码"].astype(str).isin(FUND_CODES)]
    else:
        df = df[df["基金简称"].astype(str).apply(
            lambda name: any(k in name for k in KEYWORDS) and is_target_fund(name)
        )]
    return df


def to_limit_number(text):
    """把“日累计限定金额”转成数字，便于排序；失败返回 None"""
    try:
        return float(str(text).replace(",", ""))
    except (ValueError, TypeError):
        return None


def main():
    df = fetch_funds()
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

    funds = []
    for _, row in df.iterrows():
        limit_raw = str(row.get("日累计限定金额", "")).strip()
        funds.append({
            "code": str(row.get("基金代码", "")).strip(),
            "name": str(row.get("基金简称", "")).strip(),
            "purchase_status": str(row.get("申购状态", "")).strip(),
            "redeem_status": str(row.get("赎回状态", "")).strip(),
            "daily_limit_raw": limit_raw,
            "daily_limit": to_limit_number(limit_raw),
            "next_open_day": str(row.get("下一开放日", "")).strip(),
        })

    # 限购金额越小排越前（限购越严越靠前），无金额的排最后
    funds.sort(key=lambda f: (f["daily_limit"] is None, f["daily_limit"] or 0))

    output = {
        "updated_at": now,
        "count": len(funds),
        "funds": funds,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"已更新 data.json，共 {len(funds)} 只基金，时间 {now}")


if __name__ == "__main__":
    main()
