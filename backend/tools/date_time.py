from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取中国标准时间。用户询问当前日期、时间或星期时调用此工具。"""
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    weekday = "一二三四五六日"[now.weekday()]
    return f"{now:%Y-%m-%d %H:%M:%S}（星期{weekday}，中国标准时间）"
