"""
自包含的行情数据采集模块（零第三方数据依赖，仅需 requests）。

数据源（全部公开、零鉴权）：
- 腾讯财经 qt.gtimg.cn  : A股/港股/美股 实时快照（GBK 编码）
- Yahoo Finance v8 chart : 美股/港股/A股 指数 N 日日K（用于趋势）
- 东财 push2 clist       : 行业 / 概念板块 涨跌排名
- 东财 push2ex           : 涨停池 / 跌停池（情绪 + 连板高度 + 题材分布）
- 同花顺 getharden       : 当日强势股「题材归因」reason tags（主线候选）
- 同花顺 hsgtApi         : 北向资金（沪股通 / 深股通）当日累计净流入

设计参考：
  https://github.com/simonlin1212/a-stock-data
  https://github.com/simonlin1212/global-stock-data
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta

import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
TIMEOUT = 15

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": UA})


def _get(url: str, *, params: dict | None = None, headers: dict | None = None,
         retries: int = 3, **kw) -> requests.Response:
    """带重试的 GET：东财 / 同花顺等接口偶发连接重置(RemoteDisconnected)，自动退避重试。"""
    last = None
    for i in range(retries):
        try:
            return _SESSION.get(url, params=params, headers=headers, timeout=TIMEOUT, **kw)
        except requests.RequestException as e:  # noqa: PERF203
            last = e
            time.sleep(0.6 * (i + 1))
    raise last  # type: ignore[misc]

# ───────────────────────── 指数清单 ─────────────────────────
# tq   = 腾讯实时代码（实时快照，所有市场可用）
# hist = (源, 代码) 历史日K：
#        "tx_a"  腾讯 A 股日K  / "tx_hk" 腾讯港股日K / "yh" Yahoo 日K / None 仅实时
A_INDICES = [
    {"name": "上证指数", "tq": "sh000001", "hist": ("tx_a", "sh000001")},
    {"name": "深证成指", "tq": "sz399001", "hist": ("tx_a", "sz399001")},
    {"name": "创业板指", "tq": "sz399006", "hist": ("tx_a", "sz399006")},
    {"name": "科创50", "tq": "sh000688", "hist": ("tx_a", "sh000688")},
    {"name": "沪深300", "tq": "sh000300", "hist": ("tx_a", "sh000300")},
    {"name": "北证50", "tq": "bj899050", "hist": ("em", "0.899050")},
]
HK_INDICES = [
    {"name": "恒生指数", "tq": "r_hkHSI", "hist": ("tx_hk", "hkHSI")},
    {"name": "恒生科技", "tq": "r_hkHSTECH", "hist": ("tx_hk", "hkHSTECH")},
    {"name": "国企指数", "tq": "r_hkHSCEI", "hist": ("tx_hk", "hkHSCEI")},
]
US_INDICES = [
    {"name": "道琼斯", "tq": "usDJI", "hist": ("yh", "^DJI")},
    {"name": "纳斯达克", "tq": "usIXIC", "hist": ("yh", "^IXIC")},
    {"name": "标普500", "tq": "usINX", "hist": ("yh", "^GSPC")},
    # 金龙中国指数(^HXC) Yahoo 日K稀疏，改用其跟踪 ETF PGJ 作为中概股代理
    {"name": "金龙中国(PGJ)", "tq": None, "hist": ("yh", "PGJ")},
]


# ───────────────────────── 腾讯实时快照 ─────────────────────────
def tencent_quotes(codes: list[str]) -> dict[str, dict]:
    """批量拉腾讯实时行情。codes 形如 ['sh000001','r_hkHSI','usDJI']。

    返回 {code: {name, price, prev_close, change_pct, amount}}。
    腾讯字段用 ~ 分隔；不同市场字段位略有差异，这里只取通用的几个。
    """
    if not codes:
        return {}
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    r = _get(url)
    r.encoding = "gbk"
    out: dict[str, dict] = {}
    for line in r.text.strip().split(";"):
        line = line.strip()
        if "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].strip().split("_", 1)[-1]  # v_sh000001 -> sh000001
        vals = line.split('"')[1].split("~")
        if len(vals) < 6:
            continue
        try:
            price = float(vals[3]) if vals[3] else 0.0
            prev = float(vals[4]) if vals[4] else 0.0
        except ValueError:
            continue
        chg = float(vals[32]) if len(vals) > 32 and vals[32] else (
            round((price / prev - 1) * 100, 2) if prev else 0.0
        )
        amount = ""
        if len(vals) > 37 and vals[37]:
            amount = vals[37]
        out[key] = {
            "name": vals[1],
            "price": price,
            "prev_close": prev,
            "change_pct": chg,
            "amount": amount,
        }
    return out


# ───────────────────────── Yahoo N 日日K ─────────────────────────
def yahoo_daily(symbol: str, days: int = 5) -> list[dict]:
    """Yahoo v8 chart 日K，返回最近 days 个交易日 [{date, close, change_pct}]。"""
    # 多取一些缓冲，避免节假日导致不足
    rng = "1mo" if days <= 20 else "3mo"
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = _get(url, params={"interval": "1d", "range": rng})
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = res.get("timestamp", [])
    closes = res["indicators"]["quote"][0].get("close", [])
    rows = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        rows.append({"date": datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"),
                     "close": round(c, 2)})
    return _attach_change(rows, days)


def _attach_change(rows: list[dict], days: int) -> list[dict]:
    """给日K序列补上日涨跌幅，并截取最近 days 天。"""
    for i in range(1, len(rows)):
        prev = rows[i - 1]["close"]
        rows[i]["change_pct"] = round((rows[i]["close"] / prev - 1) * 100, 2) if prev else 0.0
    if rows:
        rows[0]["change_pct"] = 0.0
    return rows[-days:]


# ───────────────────────── 腾讯 N 日日K（A股 / 港股） ─────────────────────────
def tencent_daily(code: str, market: str, days: int = 5) -> list[dict]:
    """腾讯日K。market: 'a'=A股(fqkline), 'hk'=港股(hkfqkline)。

    code: A股形如 'sh000001'；港股形如 'hkHSI'（去掉实时代码的 r_ 前缀）。
    返回最近 days 个交易日 [{date, close, change_pct}]。
    """
    endpoint = "hkfqkline" if market == "hk" else "fqkline"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/{endpoint}/get"
    r = _get(url, params={"param": f"{code},day,,,{days + 10},qfq"})
    node = (r.json().get("data") or {}).get(code) or {}
    klines = node.get("qfqday") or node.get("day") or []
    rows = [{"date": k[0], "close": round(float(k[2]), 2)} for k in klines if len(k) >= 3]
    return _attach_change(rows, days)


# ───────────────────────── 东财 N 日日K ─────────────────────────
def eastmoney_daily(secid: str, days: int = 5) -> list[dict]:
    """东财 push2his 日K。secid 形如 '0.899050'（北证50）。"""
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {"secid": secid, "fields1": "f1", "fields2": "f51,f53",
              "klt": "101", "fqt": "1", "end": "20500101", "lmt": str(days + 10)}
    r = _get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"})
    klines = (r.json().get("data") or {}).get("klines") or []
    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) >= 2:
            rows.append({"date": parts[0], "close": round(float(parts[1]), 2)})
    return _attach_change(rows, days)


def fetch_history(hist: tuple[str, str] | None, days: int) -> list[dict]:
    """按指数的 hist 配置取历史日K。"""
    if not hist:
        return []
    src, code = hist
    if src == "tx_a":
        return tencent_daily(code, "a", days)
    if src == "tx_hk":
        return tencent_daily(code, "hk", days)
    if src == "em":
        return eastmoney_daily(code, days)
    if src == "yh":
        return yahoo_daily(code, days)
    return []


# ───────────────────────── 个股行情（A股 / 港股 / 美股） ─────────────────────────
def _a_prefix(code: str) -> str:
    """A 股 6 位代码 → 腾讯前缀代码。6/9→sh，8/4→bj，其余→sz。"""
    code = code.strip().upper().replace("SH", "").replace("SZ", "").replace("BJ", "")
    code = code.split(".")[0]
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("8", "4")):
        return f"bj{code}"
    return f"sz{code}"


def _tq_code(code: str, market: str) -> str:
    """个股代码 → 腾讯实时代码。"""
    if market == "a":
        return _a_prefix(code)
    if market == "hk":
        return f"r_hk{code.zfill(5)}"
    return f"us{code.upper()}"  # 美股


def stock_quote(code: str, market: str) -> dict:
    """单只个股实时行情。market: 'a'/'hk'/'us'。

    返回 {code, name, price, prev_close, change_pct, amount}（取不到返回 {}）。
    """
    tq = _tq_code(code, market)
    snap = tencent_quotes([tq])
    rec = snap.get(tq.split("_", 1)[-1]) or snap.get(tq) or {}
    if rec:
        rec = {"code": code, **rec}
    return rec


def stock_history(code: str, market: str, days: int = 5) -> list[dict]:
    """单只个股近 days 日日K [{date, close, change_pct}]。"""
    if market == "a":
        return tencent_daily(_a_prefix(code), "a", days)
    if market == "hk":
        return tencent_daily(f"hk{code.zfill(5)}", "hk", days)
    return yahoo_daily(code.upper(), days)  # 美股


# ───────────────────────── 东财板块排名 ─────────────────────────
def eastmoney_boards(board_type: int = 2, top: int = 10) -> dict:
    """东财板块涨跌排名。board_type: 2=行业, 3=概念。

    返回 {top: [...], bottom: [...]}，每项 {name, change_pct, up, down, leader}。
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "500", "po": "1", "np": "1", "fltt": "2", "invt": "2",
        "fid": "f3", "fs": f"m:90+t:{board_type}",
        "fields": "f3,f12,f14,f104,f105,f128,f140",
    }
    r = _get(url, params=params)
    diff = (r.json().get("data") or {}).get("diff") or []
    rows = [{
        "name": it.get("f14", ""),
        "change_pct": it.get("f3", 0),
        "up": it.get("f104", 0),
        "down": it.get("f105", 0),
        "leader": it.get("f128", ""),
    } for it in diff]
    rows.sort(key=lambda x: (x["change_pct"] if isinstance(x["change_pct"], (int, float)) else -999),
              reverse=True)
    return {"total": len(rows), "top": rows[:top], "bottom": rows[-top:][::-1]}


# ───────────────────────── 涨停 / 跌停池 ─────────────────────────
def _zt_dt_pool(kind: str, date: str) -> list[dict]:
    """kind: 'zt'=涨停, 'dt'=跌停。date: YYYYMMDD。"""
    api = "getTopicZTPool" if kind == "zt" else "getTopicDTPool"
    url = f"https://push2ex.eastmoney.com/{api}"
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989", "dpt": "wz.ztzt",
        "Pageindex": "0", "pagesize": "600",
        "sort": "fbt:asc" if kind == "zt" else "fund:asc", "date": date,
    }
    r = _get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"})
    pool = (r.json().get("data") or {}).get("pool") or []
    out = []
    for it in pool:
        out.append({
            "code": it.get("c", ""),
            "name": it.get("n", ""),
            "industry": it.get("hybk", ""),     # 行业板块
            "lbc": it.get("lbc", 0),            # 连板数
            "zbc": it.get("zbc", 0),            # 炸板次数
        })
    return out


def limit_pool(date: str) -> dict:
    """涨停 / 跌停池汇总，自动回退到最近有数据的交易日。

    返回 {date, zt_count, dt_count, max_lb, lb_dist, industry_dist, dragons}。
    """
    d = date
    for _ in range(7):  # 最多回退 7 天找有数据的交易日
        zt = _zt_dt_pool("zt", d)
        if zt:
            break
        d = (datetime.strptime(d, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
    dt = _zt_dt_pool("dt", d)

    # 连板高度分布 + 行业分布 + 龙头（连板最高的前几只）
    lb_dist: dict[int, int] = {}
    ind_dist: dict[str, int] = {}
    for s in zt:
        lb = int(s.get("lbc") or 1)
        lb_dist[lb] = lb_dist.get(lb, 0) + 1
        ind = s.get("industry") or "其他"
        ind_dist[ind] = ind_dist.get(ind, 0) + 1
    dragons = sorted(zt, key=lambda x: int(x.get("lbc") or 0), reverse=True)[:8]
    return {
        "date": d,
        "zt_count": len(zt),
        "dt_count": len(dt),
        "max_lb": max(lb_dist) if lb_dist else 0,
        "lb_dist": dict(sorted(lb_dist.items(), reverse=True)),
        "industry_dist": dict(sorted(ind_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
        "dragons": [{"name": s["name"], "code": s["code"], "lbc": s["lbc"],
                     "industry": s["industry"]} for s in dragons],
    }


# ───────────────────────── 同花顺题材归因 ─────────────────────────
def ths_theme_tags(date: str | None = None, top: int = 15) -> dict:
    """同花顺当日强势股题材归因，统计 reason 标签词频 → 主线候选。

    date: YYYY-MM-DD，None=今天。返回 {count, tags: [(tag, n)...], samples: [...]}。
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    url = (f"http://zx.10jqka.com.cn/event/api/getharden/"
           f"date/{date}/orderby/date/orderway/desc/charset/GBK/")
    r = _get(url)
    d = r.json()
    rows = d.get("data") or []
    from collections import Counter
    cnt: Counter = Counter()
    for row in rows:
        reason = str(row.get("reason") or "")
        for tag in re.split(r"[+＋、,，\s]+", reason):
            tag = tag.strip()
            if tag:
                cnt[tag] += 1
    samples = [{"name": r.get("name"), "zhangfu": r.get("zhangfu"),
                "reason": r.get("reason")} for r in rows[:10]]
    return {"date": date, "count": len(rows),
            "tags": cnt.most_common(top), "samples": samples}


# ───────────────────────── 北向资金 ─────────────────────────
def northbound() -> dict:
    """同花顺北向资金当日分钟流向，返回收盘累计 {hgt_yi, sgt_yi, total_yi}。

    注：eastmoney 北向净额自 2024-08 起断供，这里用同花顺 hsgtApi。
    沪深港通额度调整后部分时段可能返回 0，属上游问题。
    """
    url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
    r = _get(url, headers={"Host": "data.hexin.cn", "Referer": "https://data.hexin.cn/"})
    d = r.json()
    n_time = len(d.get("time") or [])

    def _leg(key: str) -> float | None:
        """仅当该条腿的分钟序列基本完整时才采用末值，避免上游断供/串档的脏数据。"""
        arr = [x for x in (d.get(key) or []) if x not in (None, "")]
        # 序列长度需达到时间轴的 80%（沪深股通净额量级通常在 ±200 亿内）
        if not arr or (n_time and len(arr) < 0.8 * n_time):
            return None
        try:
            return float(arr[-1])
        except (TypeError, ValueError):
            return None

    h = _leg("hgt")
    s = _leg("sgt")
    total = round((h or 0) + (s or 0), 2) if (h is not None and s is not None) else None
    return {"hgt_yi": h, "sgt_yi": s, "total_yi": total, "points": n_time}


# ───────────────────────── 指数 N 日趋势聚合 ─────────────────────────
def index_block(indices: list[dict], days: int = 5) -> list[dict]:
    """对一组指数取实时快照 + N 日趋势。"""
    tq_codes = [x["tq"] for x in indices if x["tq"]]
    snap = tencent_quotes(tq_codes)
    out = []
    for idx in indices:
        rec = {"name": idx["name"], "realtime": None, "history": []}
        if idx["tq"] and idx["tq"] in snap:
            rec["realtime"] = snap[idx["tq"]]
        if idx.get("hist"):
            try:
                rec["history"] = fetch_history(idx["hist"], days)
            except Exception as e:  # noqa: BLE001
                rec["history_error"] = repr(e)[:80]
        out.append(rec)
    return out


def collect(days: int = 5, date: str | None = None) -> dict:
    """采集全部数据。date 用于涨停池 / 题材（YYYYMMDD / None=今天）。"""
    today = datetime.now()
    ymd = date or today.strftime("%Y%m%d")
    ths_date = (date[:4] + "-" + date[4:6] + "-" + date[6:8]) if date else today.strftime("%Y-%m-%d")

    data: dict = {"generated_at": today.strftime("%Y-%m-%d %H:%M:%S"), "lookback_days": days}

    def safe(name, fn):
        try:
            data[name] = fn()
        except Exception as e:  # noqa: BLE001
            data[name] = {"error": repr(e)[:120]}

    safe("us", lambda: index_block(US_INDICES, days))
    safe("hk", lambda: index_block(HK_INDICES, days))
    safe("a", lambda: index_block(A_INDICES, days))
    safe("industry_boards", lambda: eastmoney_boards(2, 10))
    safe("concept_boards", lambda: eastmoney_boards(3, 10))
    safe("limit_pool", lambda: limit_pool(ymd))
    safe("theme_tags", lambda: ths_theme_tags(ths_date, 15))
    safe("northbound", northbound)
    return data


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="行情数据采集自检")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--date", default=None, help="YYYYMMDD，默认今天")
    ap.add_argument("--json", action="store_true", help="输出完整 JSON")
    args = ap.parse_args()

    result = collect(days=args.days, date=args.date)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])
