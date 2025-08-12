
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple

class Utils:
  @classmethod
  def _process_time_params(cls, since: Optional[str], until: Optional[str], 
                        relative: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """处理时间参数，相对时间优先级高于绝对时间，默认使用今天的日期"""
        # 获取当前UTC时间（带时区信息）
        current_utc = datetime.now()
        
        # 处理相对时间（优先级最高）
        if relative:
            time_deltas = {
                '24hours': timedelta(hours=24),
                '3days': timedelta(days=3),
                '1week': timedelta(weeks=1),
                '1month': timedelta(days=30)
            }
            
            if relative not in time_deltas:
                raise ValueError(
                    f"无效的相对时间选项: {relative}. "
                    f"有效值为: {list(time_deltas.keys())}"
                )
            
            until_dt = current_utc
            since_dt = until_dt - time_deltas[relative]
            
            # 转换为ISO格式并添加'Z'表示UTC时间
            since = since_dt.isoformat()
            until = until_dt.isoformat()
        
        # 处理绝对时间，为空时使用今天的日期
        else:
            # 获取今天UTC 0点（保留时区信息）
            today_utc = current_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if not since:
                since = today_utc.isoformat()
            
            if not until:
                # 明天UTC 0点作为默认结束时间
                tomorrow_utc = today_utc + timedelta(days=1)
                until = tomorrow_utc.isoformat()
        
        return since, until
    
  @classmethod
  def _get_relative_time_desc(cls, relative_time: str) -> str:
        """获取相对时间的描述文本"""
        desc_map = {
            "24hours": "过去24小时",
            "3day": "过去3天",
            "1week": "过去1周",
            "1month": "过去1个月"
        }
        return desc_map.get(relative_time, relative_time)

  @classmethod
  def _parse_repo(cls, repo: str) -> tuple:
        """解析仓库字符串为所有者和仓库名"""
        parts = repo.split("/")
        if len(parts) != 2:
            raise ValueError("仓库格式错误，请使用 'owner/repo' 格式")
        return parts[0], parts[1]

  @classmethod
  def format_date(cls, time_str: str) -> str:
        """
        将ISO格式时间字符串格式化为"年-月-日 时:分:秒"格式（不含微秒）
        
        参数:
            time_str: ISO格式时间字符串（如"2025-08-10T20:54:54.556954"）
        
        返回:
            格式化后的时间字符串（如"2025-08-10 20:54:54"）
        """
        # 解析ISO格式时间字符串为datetime对象
        dt = datetime.fromisoformat(time_str)
        
        # 清除微秒部分
        dt_no_ms = dt.replace(microsecond=0)
        
        # 格式化为标准时间字符串
        return dt_no_ms.strftime("%Y-%m-%d %H:%M:%S")
