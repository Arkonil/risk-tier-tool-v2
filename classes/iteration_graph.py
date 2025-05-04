import pandas as pd

from classes.iteration import IterationSingleVar, IterationDoubleVar

def __integer_generator():
    current = 0
    while True:
        current += 1
        yield current

__generator = __integer_generator()

def new_id():
    return str(next(__generator))

class IterationGraph:
    
    def __init__(self) -> None:
        self.iterations: dict[str, IterationSingleVar | IterationDoubleVar] = {}
        self.connections = {}
        
        self.current_selected_node_id = None
        self.viewing_node_id = None
        
    def iteration_depth(self, node_id: str) -> int:
        if isinstance(self.iterations[node_id], IterationSingleVar):
            return 1
        elif node_id in self.connections:
            return 2
        else:
            return 3
        
    def get_descendants(self, node_id) -> list[str]:
        if node_id not in self.connections:
            return []
        
        descendants = self.connections[node_id]
        for descendant in descendants:
            descendants += self.get_descendants(descendant)
            
        return descendants
    
    def get_parent(self, node_id) -> str:
        for parent, children in self.connections.items():
            if node_id in children:
                return parent
        
    def select_node_id(self, node_id: str = None):        
        if node_id in self.iterations:
            self.current_selected_node_id = node_id
        else:
            self.current_selected_node_id = None
            
    def select_viewing_node_id(self, node_id: str = None):
        if node_id in self.iterations:
            self.viewing_node_id = node_id
        else:
            self.viewing_node_id = None
            
    def add_single_var_node(self, variable: pd.Series):
        new_node_id = new_id()
        iteration = IterationSingleVar(id=new_node_id, variable=variable)
        
        self.iterations[new_node_id] = iteration
        self.connections[new_node_id] = []
        
        self.select_node_id(new_node_id)
        
    def add_double_var_node(self, previous_node_id: str, variable: pd.Series):
        new_node_id = new_id()
        iteration = IterationDoubleVar(id=new_node_id, previos_iteration=self.iterations[previous_node_id], variable=variable)
        
        self.iterations[new_node_id] = iteration
        
        if self.iteration_depth(previous_node_id) == 1:
            self.connections[new_node_id] = []
        
        self.connections[previous_node_id].append(new_node_id)    
        
        self.select_node_id(new_node_id)
        
    def delete_iteration(self, node_id: str):
        nodes_to_delete = [node_id] + self.get_descendants(node_id)
        
        for node in nodes_to_delete:
            del self.iterations[node]
            if node in self.connections:
                del self.connections[node]
                
        for parent, children in self.connections.items():
            self.connections[parent] = [child for child in children if child not in nodes_to_delete]
            
        self.select_node_id()
        