from abc import ABC, abstractmethod
from typing import Any

class TextProcessingStage(ABC):
    """
    Pluggable stage interface for the text processor pipeline.
    """
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """Execute the stage with provided arguments."""
        pass
