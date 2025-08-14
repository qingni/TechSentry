from datetime import datetime, timedelta
from typing import Optional, Tuple

class Utils:
    # 统一的时间定义数据结构
    relative_time_options = {
        '24hours': {
            'delta': timedelta(hours=24),
            'desc': '24 hours'
        },
        '3days': {
            'delta': timedelta(days=3),
            'desc': '3 days'
        },
        '1week': {
            'delta': timedelta(weeks=1),
            'desc': '1 week'
        },
        '1month': {
            'delta': timedelta(days=30),
            'desc': '1 month'
        }
    }

    @classmethod
    def _process_time_params(cls, since: Optional[str], until: Optional[str], 
                        relative: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """处理时间参数，相对时间优先级高于绝对时间，默认使用今天的日期"""
        # 获取当前UTC时间（带时区信息）
        current_utc = datetime.now()
        
        # 处理相对时间（优先级最高）
        if relative:
            if relative not in cls.relative_time_options:
                raise ValueError(
                    f"无效的相对时间选项: {relative}. "
                    f"有效值为: {list(cls.relative_time_options.keys())}"
                )
            
            until_dt = current_utc
            since_dt = until_dt - cls.relative_time_options[relative]['delta']
            
            # 转换为ISO格式并添加'Z'表示UTC时间
            since = since_dt.isoformat()
            until = until_dt.isoformat()
        
        # 处理绝对时间，为空时使用今天的日期
        else:
            # 两者都为空：当前时间为结束，往前推一天为开始
            if not since and not until:
                until_dt = current_utc
                since_dt = until_dt - timedelta(days=1)
                since = since_dt.isoformat()
                until = until_dt.isoformat()
            
            # since为空：基于until往前推一天
            elif not since and until:
                until_dt = datetime.fromisoformat(until)
                since_dt = until_dt - timedelta(days=1)
                since = since_dt.isoformat()
            
            # until为空：基于since往后推一天
            elif since and not until:
                since_dt = datetime.fromisoformat(since)
                until_dt = since_dt + timedelta(days=1)
                until = until_dt.isoformat()
        
        return since, until
    
    @classmethod
    def _get_relative_time_desc(cls, relative_time: str) -> str:
        """获取相对时间的描述文本"""
        return cls.relative_time_options.get(relative_time, {}).get('desc', relative_time)
        
    @classmethod
    def get_all_relative_time_descriptions(cls) -> list[str]:
        """获取所有相对时间选项的描述文本列表"""
        return [option['desc'] for option in cls.relative_time_options.values()]
        
    @classmethod
    def get_key_by_description(cls, desc: str) -> Optional[str]:
        """通过描述文本获取对应的relative_time选项的key"""
        for key, option in cls.relative_time_options.items():
            if option['desc'] == desc:
                return key
        return None

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
        将ISO格式时间字符串格式化为"年-月-日"格式
        
        参数:
            time_str: ISO格式时间字符串（如"2025-08-10T20:54:54.556954"）
        
        返回:
            格式化后的时间字符串（如"2025-08-10"）
        """
        # 解析ISO格式时间字符串为datetime对象
        dt = datetime.fromisoformat(time_str)
        
        # 清除微秒部分
        dt_no_ms = dt.replace(microsecond=0)
        
        # 格式化为标准时间字符串
        return dt_no_ms.strftime("%Y-%m-%d")