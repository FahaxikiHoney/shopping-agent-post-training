from abc import ABC, abstractmethod
from core.data_models import Trajectory, DimensionResult


class BaseDimension(ABC):
    dimension_id: str
    dimension_label: str

    @abstractmethod
    def evaluate(self, trajectory: Trajectory) -> DimensionResult:
        ...
