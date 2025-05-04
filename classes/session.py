from classes.data import Data
from classes.scalars import Scalar
from classes.iteration_graph import IterationGraph

class Session():
    
    def __init__(self):
        super().__init__()
        
        self.data = Data()
        self.dlr_scalars = Scalar("dlr")
        self.ulr_scalars = Scalar("ulr")
        self.iteration_graph = IterationGraph()
