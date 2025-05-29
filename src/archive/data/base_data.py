from abc import ABC, abstractmethod
import pandas as pd

class Data(ABC):
    def __init__(self):
        self.df = pd.DataFrame()

    @abstractmethod
    def fetch(self):
        """Fetch data from the source"""
        pass

    @abstractmethod
    def process(self):
        """Process the fetched data"""
        pass