# -*- coding: utf-8 -*-
"""玩法总入口。

为了降低维护难度，具体玩法已经拆到：
- construction.py：土建、设备安装、目标与变体；
- commissioning.py：系统调试、装料与零功率物理试验；
- operation.py：并网运行、预警/故障、剂量作业、维护升级；
- parameter_system.py：所有参数计算和参数影响。

engine.py 仍然只需要导入 GameplayMixin。
"""

from .construction import ConstructionMixin
from .commissioning import CommissioningMixin
from .operation import OperationMixin
from .accident_system import AccidentSystemMixin
from .parameter_system import ParameterSystemMixin


class GameplayMixin(ConstructionMixin, CommissioningMixin, AccidentSystemMixin, OperationMixin, ParameterSystemMixin):
    pass
