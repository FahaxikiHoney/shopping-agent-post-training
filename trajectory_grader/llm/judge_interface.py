from abc import ABC, abstractmethod
from core.data_models import Trajectory, DimensionResult


class JudgeInterface(ABC):
    """统一 LLM judge 接口，屏蔽 mock/real 差异。"""

    @abstractmethod
    def evaluate(self, dimension_id: str, dimension_label: str, trajectory: Trajectory) -> DimensionResult:
        ...

    @abstractmethod
    def get_judge_name(self) -> str:
        ...
