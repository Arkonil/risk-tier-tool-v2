from classes.data import Data
from classes.home_page_state import HomePageState
from classes.scalars import Scalar
from classes.iteration_graph import IterationGraph
from classes.options import Options
from classes.constants import LossRateTypes


class Session:
    def __init__(self):
        super().__init__()

        self.data = Data()
        self.dlr_scalars = Scalar(LossRateTypes.DLR)
        self.ulr_scalars = Scalar(LossRateTypes.ULR)
        self.iteration_graph = IterationGraph()
        self.home_page_state = HomePageState()
        self.options = Options()
