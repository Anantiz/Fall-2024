from enum import Enum
import sys
import math as m
import time
from collections import deque

global LOGGING_PARSING
global EPSILON
global POD_PRICE
global TUBE_PRICE
global NOT_ENOUGH_RESOURCES

LOGGING_PARSING = True
EPSILON = 0.00001
NOT_ENOUGH_RESOURCES = -2
POD_PRICE = 1000
TUBE_PRICE = 10

def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)

class UniqueFIFOQueue:
    def __init__(self):
        self.queue = deque()  # For maintaining order
        self.elements = set()  # For uniqueness check

    def enqueue(self, item):
        """Add an item to the queue if it is not already present."""
        if item not in self.elements:
            self.queue.append(item)
            self.elements.add(item)

    def dequeue(self):
        """Remove and return the first item from the queue."""
        if self.queue:
            item = self.queue.popleft()  # Remove from the queue (FIFO)
            self.elements.remove(item)  # Remove from the set to maintain uniqueness
            return item
        return None

    def add_front(self, item):
        """Add an item to the front of the queue."""
        if item not in self.elements:
            self.queue.appendleft(item)
            self.elements.add(item)

    def __len__(self):
        """Return the number of elements in the queue."""
        return len(self.queue)


### GLOBAL VARIABLES ###

class SimModel:
    def __init__(self) -> None:
        # id: Building
        self.buildings = {}
        # id: (Tube/Teleporter, building_id1, building_id2)
        self.tubes = {}
        self.teleporters = {}
        # id: Pod
        self.pods = {}
        self.routes = {} # Don't know how to use this yet
        self.resources = 0
        self.round = -1
        self.action_queue = UniqueFIFOQueue()

    def parse_input(self):
        self.round += 1
        self.resources = int(input())
        if LOGGING_PARSING:
            log(f"Resources: {self.resources}")

        self.num_travel_routes = int(input())
        for i in range(self.num_travel_routes):
            building_id_1, building_id_2, capacity = [int(j) for j in input().split()]
            self.routes[(building_id_1, building_id_2)] = capacity

        num_pods = int(input())
        for i in range(num_pods):
            pod_properties = input()
            if LOGGING_PARSING:
                log(f"Pod properties: {pod_properties}")

        num_new_buildings = int(input())
        for i in range(num_new_buildings):
            building_properties = input()
            data = list(map(int, building_properties.split()))
            if (data[0] == 0):
                self.buildings[data[1]] = LandingPad(data[2], data[3], data[1])
                self.buildings[data[1]].set_astronauts(*data[5:])
            else:
                self.buildings[data[1]] = Module(data[0], data[2], data[3], data[1])
            if LOGGING_PARSING:
                log(self.buildings[data[1]].__str__())

    def get_unconected_pad(self):
        for b in self.buildings.values():
            if isinstance(b, LandingPad):
                if b.is_isolated():
                    return b
        return None

    def bill(self, amount):
        self.resources -= amount
        if LOGGING_PARSING:
            log(f"Billed: {amount}, Remaining: {self.resources}")
###########################################################

G_model = SimModel()

###########################################################
#  ██████ ██       █████  ███████ ███████ ███████ ███████ #
# ██      ██      ██   ██ ██      ██      ██      ██      #
# ██      ██      ███████ ███████ ███████ █████   ███████ #
# ██      ██      ██   ██      ██      ██ ██           ██ #
#  ██████ ███████ ██   ██ ███████ ███████ ███████ ███████ #
###########################################################



class BuildingClass(Enum):
    PAD = 0
    MODULE = 1



class TeleporterState(Enum):
    Eingang = 0
    Ausgang = 1
    Frei = 2

class Point:
    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y

    def distance(self, point):
        return m.sqrt((self.x - point.x)**2 + (self.y - point.y)**2)

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"

    def __eq__(self, o: object) -> bool:
        return self.x == o.x and self.y == o.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __add__(self, point):
        return Point(self.x + point.x, self.y + point.y)

    def __sub__(self, point):
        return Point(self.x - point.x, self.y - point.y)

    def __mul__(self, point):
        return Point(self.x * point.x, self.y * point.y)

    def __truediv__(self, point):
        return Point(self.x / point.x, self.y / point.y)

    def __floordiv__(self, point):
        return Point(self.x // point.x, self.y // point.y)

class Building:

    def __init__(self, building_class: BuildingClass, type: int, x: int, y: int, id: int) -> None:
        self.x = x
        self.y = y
        self.pos = Point(x, y)
        self.building_class = building_class
        self.type = type
        self.id = id
        self.tp_state = TeleporterState.Frei
        self.tp_with = None
        self.tube_connections = dict() # tube_id, other_building_id
        self.conected_buildings_ids = set()
        self.conected_tubes = dict()

    def set_teleporter(self, state: TeleporterState, other_building):
        self.tp_state = state
        self.tp_with = other_building

    def add_tube_connection(self, tube):
        other_building = tube.b1.id if tube.b2.id == self.id else tube.b2.id
        self.tube_connections[tube.id] = other_building
        self.conected_tubes[tube.id] = tube

    def wake_tube(self, tube_id):
        """ Means a pod is using the tube """
        self.conected_buildings_ids.add(self.tube_connections[tube_id])

    ### DANGER FUNCTION ###
    def sleep_tube(self, tube_id):
        """
        REALY BAD FUNCTION, DON'T USE IT AS IT IS NOW
        Means a pod is not using the tube
        """
        self.conected_buildings_ids.remove(self.tube_connections[tube_id])

    def is_unconected(self, network: set[int]) -> bool:
        for building_id in network:
            if self.id == building_id:
                return False
            if building_id in self.conected_buildings_ids:
                return False
        return True

    def is_isolated(self):
        if len(self.conected_buildings_ids) <= 1:
            return True
        return False

    def get_network(self) -> set[int]:
        """ Returns a set of all the buildings that are connected to this building """
        network = set()
        network.add(self.id)
        for building_id in self.conected_buildings_ids:
            network.add(building_id)
        return network

class LandingPad(Building):
    def __init__(self, x, y, id) -> None:
        super().__init__(BuildingClass.PAD, -1, x, y, id)
        self.astronauts = {}
        for i in range(1, 21):
            self.astronauts[i] = 0

    def __str__(self) -> str:
        population = ""
        for i in range(1, 21):
            if self.astronauts[i] > 0:
                population += f"{i}:{self.astronauts[i]} "
        return f"Lunar pad: id={self.id} pos={self.pos} Astronauts{population}"

    def set_astronauts(self, *astraunaut_types):
        for astronaut_type in astraunaut_types:
            self.astronauts[astronaut_type] = self.astronauts[astronaut_type] + 1

    def clear_astronauts(self):
        for i in range(1, 21):
            self.astronauts[i] = 0

    def get_type_population(self, type: int):
        return self.astronauts[type]

class Module(Building):
    def __init__(self, type, x, y, id) -> None:
        super().__init__(BuildingClass.MODULE, type, x, y, id)

    def __str__(self) -> str:
        return f"Cute Moon House: id={self.id} pos={self.pos} type={self.type}"

class Tube:
    def __init__(self, building_1, building_2, id) -> None:
        self.id = id
        self.b1 = building_1
        self.b2 = building_2
        self.start = building_1.pos
        self.end = building_2.pos
        self.capacity = 1
        self.inital_cost = self.start.distance(self.end)

    def get_upgrade_cost(self):
        return self.inital_cost * (self.capacity + 1)

    def upgrade(self):
        self.capacity += 1

class Teleporter:
    def __init__(self, building_1, building_2, id) -> None:
        self.id = id
        self.b1 = building_1
        self.b2 = building_2

################################################################
# ███    ███ ███████ ████████ ██   ██  ██████  ██████  ███████ #
# ████  ████ ██         ██    ██   ██ ██    ██ ██   ██ ██      #
# ██ ████ ██ █████      ██    ███████ ██    ██ ██   ██ ███████ #
# ██  ██  ██ ██         ██    ██   ██ ██    ██ ██   ██      ██ #
# ██      ██ ███████    ██    ██   ██  ██████  ██████  ███████ #
################################################################

### Actions ###
# Each action will return a (cost, conectivity_score) tuple
# The score will be computed based on it's impact on the graph connectivity

def will_overlap_building(start, end, other) -> bool:
    """Some math logic"""
    if abs(start.distance(end) - (start.distance(other) + other.distance(end))) < EPSILON:
        return True
    return False

def will_overlap_tube(start, end, other_start, other_end) -> bool:
    """Some math magic"""
    vec_a = end - start
    vec_b = other_end - other_start
    # Calculate the intersection point
    t = ((other_start.x - start.x) * vec_b.y - (other_start.y - start.y) * vec_b.x) / (vec_a.x * vec_b.y - vec_a.y * vec_b.x + EPSILON)
    if (t < 0 or t > 1):
        return False
    return True

def tube_is_valid(building_id1, building_id2, model=G_model) -> bool:
    """
    Check if the tube will overlap with any other tube, if it will cross any building
    """
    if  building_id1 is None or building_id2 is None or \
        building_id1 == building_id2 or model.tubes.get((building_id1, building_id2)) != None:
        return False
    b1_pos = model.buildings.get(building_id1).pos
    b2_pos = model.buildings.get(building_id2).pos
    # Will the new tube cross over an existing tube
    for tube in model.tubes.values():
        if will_overlap_tube(b1_pos, b2_pos, tube.start, tube.end):
            return False
    # Will the tube cross over a building
    for building in model.buildings.values():
        if building.id == building_id1 or building.id == building_id2:
            continue
        if will_overlap_building(b1_pos, b2_pos, building.pos):
            return False
    return True

def tube_cost(building_id1, building_id2, model=G_model) -> int:
    return model.buildings[building_id1].pos.distance(model.buildings[building_id2].pos) * 10

def action_tube(building_id1, building_id2, model=G_model) -> tuple[int, int]:
    if tube_is_valid(building_id1, building_id2, model) == False:
        return (-1, 0)
    b1 = model.buildings[building_id1]
    b2 = model.buildings[building_id2]
    cost = b1.pos.distance(b2.pos) * 10
    if model.resources < cost:
        return (NOT_ENOUGH_RESOURCES, 0)
    score = 1
    tid = len(model.tubes)
    tube = Tube(b1, b2, tid)
    model.tubes[tid] = tube
    b1.add_tube_connection(tube)
    b2.add_tube_connection(tube)
    return (cost, score)

def action_upgrade_tube(building_id1, building_id2, tube_id, model=G_model) -> tuple[int, int]:
    tube = model.tubes.get(tube_id)
    if tube == None:
        return (-1, 0)
    cost = tube.get_upgrade_cost()
    if model.resources < cost:
        return (NOT_ENOUGH_RESOURCES, 0)
    score = 1

    return (cost, score)

def action_teleport(building_entrance_id, building_ausgang_id, model=G_model) -> tuple[int, int]:
    """
    Any building can only ever be an entrance or an ausgang, not both, and only one of each
    """
    if model.resources < 5000:
        return (NOT_ENOUGH_RESOURCES, 0)

    if model.buildings[building_entrance_id].tp_state != TeleporterState.Frei or model.buildings[building_ausgang_id].tp_state != TeleporterState.Frei:
        return (-1, 0)
    model.buildings[building_entrance_id].set_teleporter_state(TeleporterState.Eingang)
    model.buildings[building_ausgang_id].set_teleporter_state(TeleporterState.Ausgang)
    model.teleporters[len(model.teleporters)] = \
        (Teleporter(building_entrance_id, building_ausgang_id, len(model.teleporters)), building_entrance_id, building_ausgang_id)
    cost = 5000
    score = 1
    # Add a magic edge to the graph, magic edges are one way not limited by capacity and can cross anything
    return (cost, score)

def action_pod(pod_id, path_building_ids: list[int], model=G_model) -> tuple[int, int]:
    cost = 1000
    if model.resources < cost:
        return (NOT_ENOUGH_RESOURCES, 0)
    score = 1


    # Add a classic edge to the graph, if tubes are available
    for b_id in path_building_ids:
        b = model.buildings.get(b_id)
        if b is None:
            return (-1, 0)
        b.wake_tube(len(model.tubes) - 1) # Dumbfuck but works for now
    model.pods[pod_id] = True # Create a Pod object with it's route on the graph later
    return (cost, score)

def action_destroy(pod_id, model=G_model) -> tuple[int, int]:
    cost = -750 # Gives back 750 resources
    score = 1
    return (cost, score)

### Quality of Life Functions ###
def print_action_tube(building_id1, building_id2):
    print(f"TUBE {building_id1} {building_id2};", end="")
def print_action_upgrade_tube(building_id1, building_id2):
    print(f"UPGRADE {building_id1} {building_id2};", end="")
def print_action_teleport(building_entrance_id, building_ausgang_id):
    print(f"TELEPORT {building_entrance_id} {building_ausgang_id};", end="")
def print_action_pod(pod_id, path_building_ids: list[int]):
    print(f"POD {pod_id} {' '.join(map(str, path_building_ids))};", end="")
def print_action_destroy(pod_id):
    print(f"DESTROY {pod_id};", end="")
def close_round():
    print("WAIT")

global G_print_actions
G_print_actions = { action_tube: print_action_tube, \
                    action_upgrade_tube: print_action_upgrade_tube, \
                    action_teleport: print_action_teleport, \
                    action_pod: print_action_pod, \
                    action_destroy: print_action_destroy}

def get_optimal_conection(network_a: set[int], network_b: set[int], model=G_model) -> Building:
    """
    Find the most optimal connection between an two networks (An isolated building is a network)
    """
    # Dumbfuck algorithm
    for building_id in network_a:
        for building_id2 in network_b:
            if tube_is_valid(building_id, building_id2):
                return model.buildings.get(building_id), model.buildings.get(building_id2)
    return None, None


###########################################################

def resolve_pending_actions(model) -> bool:
    ### For action that couldn't be performed earlier
    while True:
        action = model.action_queue.dequeue()
        if action == None:
            log("No more pending actions")
            break
        ret = action[0]()
        if ret[0] == NOT_ENOUGH_RESOURCES:
            model.action_queue.add_front(action)
            return False
        else:
            model.bill(ret[0])
            action[1]()
    return True

def naive_algorithm(model=G_model):

    if resolve_pending_actions(model) == False:
        return # All pending actions weren't done

    source = model.get_unconected_pad()
    if source is None:
        return
    source_network = source.get_network()
    for building in model.buildings.values():
        if building is source_network:
            continue
        if building.is_unconected(source_network):
            b_network_a, b_network_b = get_optimal_conection(building.get_network(), source_network)
            if b_network_a is None or b_network_b is None:
                log(f"Id {building.id} cannot be linked to network")
                continue
            ida = b_network_a.id
            idb = b_network_b.id
            if tube_is_valid(ida, idb):
                if tube_cost(ida, idb) + POD_PRICE > model.resources:
                    model.action_queue.enqueue((lambda: action_tube(ida, idb), lambda: print_action_tube(ida, idb)))
                    model.action_queue.enqueue((lambda: action_pod(len(model.pods), (ida, idb, ida)), lambda: print_action_pod(len(model.pods), (ida, idb, ida))))
                    log(f"Queued tube and pod between {ida} and {idb}")
                    continue
                ret = action_tube(ida, idb)
                model.bill(ret[0])
                print_action_tube(ida, idb)
                ret = action_pod(len(model.pods), [ida, idb, ida])
                model.bill(ret[0])
                print_action_pod(len(model.pods), [ida, idb, ida])


###################################
# ███    ███  █████  ██ ███    ██ #
# ████  ████ ██   ██ ██ ████   ██ #
# ██ ████ ██ ███████ ██ ██ ██  ██ #
# ██  ██  ██ ██   ██ ██ ██  ██ ██ #
# ██      ██ ██   ██ ██ ██   ████ #
###################################
# Game loop
while True:
    start_time = time.time()
    G_model.parse_input() # Parse the input and performs other initializations

    naive_algorithm()

    log(f"Time: {int((time.time() - start_time) * 1000)} ms")
    close_round()