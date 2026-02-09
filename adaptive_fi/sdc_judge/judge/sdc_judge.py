"""
SDC判断模块 - 独立的SDC检测和结果管理

提供独立的SDC判断功能，不依赖实验运行时流程。
用于批量处理已有实验结果，判断输出是否为SDC。
"""

import json
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .sdc_comparator import SDCComparator, CompareResult
from ..config_manager import ConfigManager


@dataclass
class SDCJudgeResult:
    """SDC判断结果数据结构"""

    log_index: int                    # 对应的log_N序号
    is_sdc: bool                      # True=SDC，False=Masked
    message: str                      # 比较详细消息
    tolerance: float                  # 使用的容差
    tolerance_type: str               # 容差类型: 'absolute' 或 'relative'
    method: str                       # 比较方法
    max_error: Optional[float] = None # 最大误差（如果有）
    test_output_path: str = ""        # 测试输出文件路径
    golden_output_path: str = ""      # Golden输出文件路径
    timestamp: str = ""               # 判断时间戳
    app_name: Optional[str] = None    # 应用名称

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class SDCJudge:
    """SDC判断器 - 用于批量判断实验结果是否为SDC"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化SDC判断器

        Args:
            config_path: applications.json路径（默认自动查找）
        """
        self.config_mgr = ConfigManager(config_path)
        self.comparator = SDCComparator()

    def judge(
        self,
        test_output: str,
        golden_output: str,
        app_name: str,
        log_index: int = -1
    ) -> SDCJudgeResult:
        """
        判断是否存在SDC

        Args:
            test_output: 测试输出文件路径
            golden_output: Golden输出文件路径
            app_name: 应用名称（用于获取比较方法和容差）
            log_index: 日志序号（用于关联实验）

        Returns:
            SDCJudgeResult对象

        Raises:
            FileNotFoundError: 如果输出文件不存在
            ValueError: 如果应用配置不存在
        """
        # 检查文件存在性
        if not os.path.exists(test_output):
            raise FileNotFoundError(f"测试输出文件不存在: {test_output}")
        if not os.path.exists(golden_output):
            raise FileNotFoundError(f"Golden输出文件不存在: {golden_output}")

        # 获取应用配置
        app_config = self.config_mgr.get_app(app_name)
        if app_config is None:
            raise ValueError(f"应用配置不存在: {app_name}")

        # 获取比较方法和容差
        method = app_config.compare_method
        tolerance = app_config.tolerance
        tolerance_type = app_config.tolerance_type

        # 执行比较
        compare_result = self.comparator.compare(
            test_output=test_output,
            golden_output=golden_output,
            method=method,
            tolerance=tolerance
        )

        # 构造判断结果
        # is_match=True 表示输出匹配（在容差范围内），即无SDC（Masked）
        # is_match=False 表示输出不匹配，即有SDC
        result = SDCJudgeResult(
            log_index=log_index,
            is_sdc=not compare_result.is_match,  # 注意：取反
            message=compare_result.message,
            tolerance=tolerance,  # 使用应用配置的容差
            tolerance_type=tolerance_type,  # 容差类型
            method=compare_result.method,
            max_error=compare_result.max_error if compare_result.max_error else None,
            test_output_path=test_output,
            golden_output_path=golden_output,
            timestamp=datetime.now().isoformat(),
            app_name=app_name
        )

        return result

    def save_result(
        self,
        result: SDCJudgeResult,
        output_dir: str
    ) -> str:
        """
        保存SDC判断结果为JSON

        Args:
            result: SDCJudgeResult对象
            output_dir: 输出目录（如sdcresult/）

        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        # 结果文件路径：sdc_{log_index}.json
        filename = f"sdc_{result.log_index}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result.to_json())

        return filepath
