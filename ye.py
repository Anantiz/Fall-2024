"""
Keywords:
    Rounds: A round is a month, 20 days are in a month

    Buildings: Buildings are nodes in a city, they can be conected by streets
        - `Landing-Pads`: Landing-Pads are buildings where dudes come from each month
        - `Hangouts`: Hangouts are buildings where dudes go to, there are 20 types of Dudes/Hangouts, Dudes go to the Hangout that matches their type

    -`Dudes`: Dudes come from Landing-Pads and go to Hangouts
    `Traffic`: The traffic is the flow of dudes in the city


    `Street`: A street is an edge conecting two buildings
    `City`: A city is a graph with Buildings as nodes and Streets as edges
    `World`: The global graph of all cities (conected or not)

    `Tubes` or `ClassicEdge` :
        - An edge is a street with a limited capacity and a travel time of 1-day.
        - They can be one-way or two-way based on Pods serving it, usefull for directing traffic
        - They can be Asleep or Awake
        - They have a limited pod-capacity, exceeding the capacity will make the pods wait for the next day
    `Teleporters` or `MagicEdge`:
        - Teleporters are one-way edges with: no capacity limit, no travel time, always Awake
        - A building can only ever host either a Teleporter Entry or Exit, and only one teleporter can be in a building
        - Teleporters do not worry about geometry, they can connect any two buildings in the world

    `Pods`:
        - Pods are used to move dudes across Tubes, a tube without a pod to serve it is considered Asleep
        - If no pod is directly available to serve a tube but one will come in a future-day, the tube is `pending`{int: day-to-wait}

    `Route`:
        - A concrete group of Nodes within a City that a Pod will visit in its route
        - Routes are directed, and should be circular

"""

from enum import Enum
import sys
import math as m
import time
from collections import deque

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

class Option:
    def __init__(self, model_action: callable, game_action: callable, model) -> None:
        self.model_action
        self.game_action
        self.model = model

    def simulate_proceed(self):
        """
        Might be used in SimModel Snapshots for simulations
        """
        ret = self.model_action()
        if isinstance(ret, int): # Error
            return ret
        self.model.score(ret)
        return 0

    def game_proceed(self):
        """
        Usually called once a list of best action has been calculated
        """
        ret = self.game_action()
        if isinstance(ret, int):
            return ret
        self.model.score(ret)
        self.game_action(ret)
        return 0

class Snapshot:
    """
    A copy of the current state of the game (SimModel)
    It has a stack and can undo actions
    """

    def __init__(self, model) -> None:
        self.queue = UniqueFIFOQueue()
        self.model = model.deepcopy()

    def push_option(self, option: object):
        """
        Action: object (Means I don't know what type of action it is)
        """
        self.queue.enqueue(option)

    def process_option(self):
        option = self.queue.dequeue()
        if option is None:
            return False
        if option.proceed() != 0:
            return False
        return True

global T_TUBE
global T_TELE
global T_CITY
global T_PODS
T_TUBE = 1
T_TELE = 2
T_CITY = 3
T_PODS = 4

global G_MODEL
global EPSILON
global LOGGING_PARSING
G_MODEL = None
EPSILON = 0.00001
LOGGING_PARSING = True

global NOTHING_TO_DO
global SUCCESS
global STANDARD_ERROR
global NO_FUNDS
global GEOMETRIC_IMPOSSIBLE
global NO_CAPACITY
global SUB_OPTIMAL
NOTHING_TO_DO = 1
SUCCESS = 0
STANDARD_ERROR = -1
NO_FUNDS = -2
GEOMETRIC_IMPOSSIBLE = -3
NO_CAPACITY = -4
SUB_OPTIMAL = -5

error_strings = {
    NOTHING_TO_DO: "Nothing to do",
    SUCCESS: "Success",
    STANDARD_ERROR: "Standard error",
    NO_FUNDS: "Not enough funds",
    GEOMETRIC_IMPOSSIBLE: "Geometrically impossible",
    NO_CAPACITY: "No capacity"
}
global POD_PRICE
global TUBE_PRICE
global TELEPORTER_PRICE
POD_PRICE = 1000
TUBE_PRICE = 10
TELEPORTER_PRICE = 5000

#################### Utils ####################
#################### Utils ####################
#################### Utils ####################

def update_dict_lists(dest: dict, src: dict):
    """
    Update a dictionary of lists with another dictionary of lists
    """
    for key, value in src.items():
        if dest.get(key) is None:
            dest[key] = value
        else:
            dest[key].extend(value)
    return dest

def make_new_city(pad, hangout, link, model):
    """
    Create a new city with a pad and a hangout, append it to the model
    """
    city = City()
    city.add_building(pad)
    city.add_building(hangout)
    city.add_link(link)
    model.cities.append(city)
    return city

def get_closest_point(src, A, B):
    """
    Return the closest point to src between A and B
    """
    if src.distance(A) < src.distance(B):
        return A
    return B

def new_dude_dict():
    return {0:0,1:0,2:0,3:0,4:0,5:0,6:0,7:0,8:0,9:0,10:0,11:0,12:0,13:0,14:0,15:0,16:0,17:0,18:0,19:0,20:0}

def add_populations(pop_list):
    """
    Add the populations of each type of dude in the list of populations
    """
    total = new_dude_dict()
    for pop in pop_list:
        for key in pop:
            total[key] += pop[key]
    return total

def path_dist(path: list[int]):
    if path is None:
        return -1
    return len(path) - 1

def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)

class BuildingClass(Enum):
    PAD = 0
    HANGOUT = 1

class TeleporterState(Enum):
    Eingang = 0
    Ausgang = 1
    Frei = 2

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

#################### EDGES ####################
#################### EDGES ####################
#################### EDGES ####################
#################### EDGES ####################
#################### EDGES ####################
class Link:
    def __init__(self, b1, b2, id, capacity) -> None:
        self.b1 = b1
        self.b2 = b2
        self.id = id
        self.capacity = capacity
        self.city = b1.city
        # Both buildings will always be in same city, since we are linking them together

    def upgrade(self):
        if self.capacity == 0 or self.capacity == 3:
            return False
        self.capacity += 1
        return True

class Tube(Link):
    tube_id_gen = 0
    def __init__(self, b1, b2) -> None:
        super().__init__(b1, b2, self.tube_id_gen, 1)
        self.tube_id_gen += 1
        self.awake = True

class Teleporter(Link):
    def __init__(self, b1, b2) -> None:
        super().__init__(b1, b2, self.tp_id_gen, 0)
        self.tp_id_gen += 1
        # Teleporter states are an enum, 0: Eingang, 1: Ausgang, 2: Frei
        b1.tp_state = TeleporterState.Eingang
        b2.tp_state = TeleporterState.Ausgang

#################### PODS ####################
#################### PODS ####################

class Pod:
    pod_id_gen = 0
    """ A pod that has a route in a city """
    def __init__(self, city, route, ) -> None:
        self.id = Pod.pod_id_gen
        Pod.pod_id_gen += 1
        self.city = city
        self.route = route
        self.city.add_pod(self)

    def announce(self):
        print_action_pod(self.id, self.route)

def create_pod(city, route: list[int]):
    if len(route) < 3:
        return SUB_OPTIMAL
    pod = Pod(city, route)
    return (1000, pod)

#################### Building ####################
#################### Building ####################

class Build:
    def __init__(self, building_class: BuildingClass, type: int, x: int, y: int, id: int) -> None:
        self.id = id
        self.x = x
        self.y = y
        self.pos = Point(x, y)
        #
        self.type = type
        self.building_class = building_class
        #
        self.tp_state = TeleporterState.Frei # Enum
        self.tp_with = None
        # GRAPH STUFF HERE
        self.city = None

    def get_adjacents(self):
        if self.city is None:
            return []
        else:
            return self.city.adjency_list[self.id]

class LandingPad(Build):
    def __init__(self, x, y, id) -> None:
        super().__init__(BuildingClass.PAD, -1, x, y, id)
        self.dudes = {}

    def __str__(self) -> str:
        return f"Lunar pad: id={self.id} pos={self.pos} dudes={self.dudes}"

    def set_dudes(self, *dude_types):
        """
        dude_types: list of types, multiple dudes of the same type will just be multiple times in the list
        """
        for dude_type in dude_types:
            if self.dudes.get(dude_type) is None:
                self.dudes[dude_type] = 1
            else:
                self.dudes[dude_type] = self.dudes[dude_type] + 1

    def get_type_population(self, type: int) -> int:
        if self.dudes.get(type) is None:
            return 0
        return self.dudes[type]

    def send_dudes(self): # Return a reference
        return self.dudes

class Hangout(Build):
    def __init__(self, type, x, y, id) -> None:
        super().__init__(BuildingClass.HANGOUT, type, x, y, id)

    def __str__(self) -> str:
        return f"Hangout: id={self.id} pos={self.pos} type={self.type}"

#################### GRAPH_STUFF ####################
#################### GRAPH_STUFF ####################

class City:
    def __init__(self) -> None:
        self.buildings_ids = set() # {id}
        self.landing_pads = dict() # {id: LandingPad}
        self.hangouts = dict() # {id: Hangout}

        # These 2 are kinda useless as it is now
        self.tubes = dict() # {id: Tube}
        self.teleporters = dict() # {id: Teleporter}

        self.pods = dict() # {id: Pod}
        self.adjency_list = dict() # {building_id: [adjacent_building_ids]}
        self.dudes = new_dude_dict() # {dude_type: population}, how many dudes of each type come in the city each month

    def graph_find_path(self, A: Build, B: Build):
        """
        Return:
        -None if A or B are not in the city
        - A list which is the shortest path from A to B
        """

        if not isinstance(A, int): # remove since we have strong typed cpp now
            A = A.id
        if not isinstance(B, int):
            B = B.id
        if A not in self.buildings_ids or B not in self.buildings_ids:
            return -1
        if A == B:
            return 0
        return search_graph(A, B, self.adjency_list)

    def add_building(self, building):
        self.buildings_ids.add(building.id)
        building.city = self
        if self.adjency_list.get(building.id) is None:
            self.adjency_list[building.id] = []

        if building.building_class == BuildingClass.HANGOUT: # Enum, to know which type of children from Building it is
            self.hangouts[building.id] = building
        elif building.building_class == BuildingClass.PAD:
            self.landing_pads[building.id] = building
            # Add the dudes that arrive to this pad each month to the city register
            pad_dudes = building.send_dudes()
            for key, value in pad_dudes.items():
                self.dudes[key] = self.dudes.get(key, 0) + value

    def add_link(self, link: Link):
        link.city = self
        if self.adjency_list.get(link.b1) is None:
            self.adjency_list[link.b1] = [link.b2]
        else:
            self.adjency_list[link.b1].append(link.b2)
        if self.adjency_list.get(link.b2) is None:
            self.adjency_list[link.b2] = [link.b1]
        else:
            self.adjency_list[link.b2].append(link.b1)
        if link.capacity == 0: # Tp have 0 capacity (unlimited)
            self.teleporters[link.id] = link
        else:
            self.tubes[link.id] = link

    def add_pod(self, pod: Pod):
        self.pods[pod.id] = pod

#################### ACTIONS ####################
#################### ACTIONS ####################
#################### ACTIONS ####################

##### Link

def will_overlap_building(start: Point, end: Point, other: Point) -> bool:
    """Some math logic"""
    if abs(start.distance(end) - (start.distance(other) + other.distance(end))) < EPSILON:
        return True
    return False

def will_overlap_tube(start: Point, end: Point, other_start: Point, other_end: Point) -> bool:
    """Some math magic to check if one point is inside the others triangle"""
    vec_a = end - start
    vec_b = other_end - other_start
    # Calculate the intersection point
    t = ((other_start.x - start.x) * vec_b.y - (other_start.y - start.y) * vec_b.x) / (vec_a.x * vec_b.y - vec_a.y * vec_b.x + EPSILON)
    if (t < 0 or t > 1):
        return False
    return True

def tube_is_valid(b1, b2, model: SimModel) -> bool:
    """
    Check if the tube will overlap with any other tube, if it will cross any building
    """
    if b1 is b2:
        return False

    # Will the new tube cross over an existing tube
    for tube in model.tubes.values():
        if will_overlap_tube(b1.pos, b2.pos, tube.start, tube.end):
            return False

    # Will the tube cross over a building
    for building in model.buildings.values():
        if building is b1 or building is b2:
            continue
        if will_overlap_building(b1.pos, b2.pos, building.pos):
            return False
    return True

def teleporter_is_valid(b1, b2) -> bool:
    if b1.tp_state != TeleporterState.Frei or b2.tp_state != TeleporterState.Frei or b1 is b2:
        return False
    return True


def link_tube(b1, b2, model, dist=None):
    """
    Create a tube between two buildings
    Return:
        int: error code
        tuple (cost, tube)
    """
    if tube_is_valid(b1, b2, model) == False:
        return GEOMETRIC_IMPOSSIBLE
    if dist is None:
        dist = b1.pos.distance(b2.pos)
    price = dist * TUBE_PRICE
    if model.resources < price:
        return NO_FUNDS
    tube = Tube(b1, b2)
    print_action_tube(b1.id, b2.id) # TODO
    return (price, tube)

def teleporter_is_valid(b1, b2) -> bool:
    if b1.tp_state != TeleporterState.Frei or b2.tp_state != TeleporterState.Frei or b1 is b2:
        return False
    return True

def link_teleporter(b1, b2, model):
    """
    Create a teleporter between two buildings
    """
    if teleporter_is_valid(b1, b2, model) == False:
        return STANDARD_ERROR
    if model.resources < 5000: # Teleporters are expensive
        return NO_FUNDS
    tp = Teleporter(b1, b2)
    print_action_teleport(b1.id, b2.id) # TODO
    return (5000, tp)

##### Connect

def conect_buildings(b1, b2, model, type=0):
    """
    Conect two buildings.
    In case of teleporters (one-way), b1 is the entrance and b2 is the exit
    Return:
        int: error code
        dict: new_objects
    """
    if b1 is None or b2 is None or b1 is b2:
        return STANDARD_ERROR
    dist = b1.pos.distance(b2.pos)

    # Default case, try to create a tube
    if type == T_TUBE:
        link_method = lambda: link_tube(b1, b2, dist=dist, model=model)
    elif type == T_TELE:
        link_method = lambda: link_teleporter(b1, b2, model)
    else:
        # FOR NOW hardcode it, make a a function that will estimate the best later
        type = T_TUBE
        link_method = lambda:  link_tube(b1, b2, dist=dist, model=model)

    err = link_method()
    if err == GEOMETRIC_IMPOSSIBLE: # Tube will overlap with another tube
        link_method = lambda: link_teleporter(b1, b2, model)
        type = T_TELE
        err = link_method()
        if err == NO_FUNDS:
            return err
    elif err == NO_FUNDS:
        return err

    new_objects = {}
    # If there where no errors, err value is a tuple (cost, [tube/teleporter])
    cost = err[0]
    model.bill(cost)
    link = err[1]
    if type == T_TUBE:
        new_objects[T_TUBE] = [link]
    else:
        new_objects[T_TELE] = [link]

    # Create city if none of the buildings are in a city
    # Add one to the other city if only one of the buildings is in a city
    # Merge the cities if both buildings are in different cities

    if b1.city is None and b2.city is None:
        if b1.building_class == BuildingClass.PAD and b2.building_class == BuildingClass.HANGOUT:
            new_objects[T_CITY] = [make_new_city(b1, b2, link, model)]
        else:
            return STANDARD_ERROR
    elif b1.city is None:
        b2.city.add_building(b1)
        b2.city.add_link(link)
    elif b2.city is None:
        b1.city.add_building(b2)
        b1.city.add_link(link)
    else:
        new_objects[T_CITY] = [merge_cities(b1.city, b2.city, b1, b2, link, model)]
    log(f"Succesfully conected {b1.id} & {b2.id}")
    return new_objects

#################### SIM MODEL ####################
#################### SIM MODEL ####################
#################### SIM MODEL ####################
#################### SIM MODEL ####################

class SimModel:
    def __init__(self) -> None:
        self.round = -1
        self.resources = 0
        self.action_queue = UniqueFIFOQueue() # Not used yet, used to store available actions if we ever want to simulate different actions
        self.cities = list()
        # Builds
        self.isolated_hangouts = set()
        self.isolated_pads = set()
        self.buildings = dict() # {id: Building}
        # Routes

        # id: object
        self.tubes = dict()
        self.teleporters = dict()
        self.pods = dict()
        self.routes = dict()
        self.dead_tubes = dict() # Tubes that are not being used within the current pod routes

    def parse_input(self):
        self.round += 1
        self.resources = int(input())
        if LOGGING_PARSING:
            log(f"Resources: {self.resources}")

        self.num_travel_routes = int(input())
        for i in range(self.num_travel_routes):
            building_id_1, building_id_2, capacity = [int(j) for j in input().split()]
            self.routes.get(building_id_1, []).append((building_id_2, capacity))
            self.routes.get(building_id_2, []).append((building_id_1, capacity))

        num_pods = int(input())
        for i in range(num_pods):
            pod_properties = input()
            if LOGGING_PARSING:
                log(f"Pod properties: {pod_properties}")

        num_new_buildings = int(input())
        for i in range(num_new_buildings):
            building_properties = input()
            # type, id, x, y | num_dudes,  dudes
            data = list(map(int, building_properties.split()))
            if (data[0] == 0):
                self.buildings[data[1]] = LandingPad(data[2], data[3], data[1])
                self.buildings[data[1]].set_dudes(*data[5:]) # Wich dudes arrive to this pad each month
                self.isolated_pads.add(self.buildings[data[1]])
            else:
                self.buildings[data[1]] = Hangout(data[0], data[2], data[3], data[1])
                self.isolated_hangouts.add(self.buildings[data[1]])
            if LOGGING_PARSING:
                log(self.buildings[data[1]].__str__())

        log(f"New buildings: {num_new_buildings}")

    def clean_isolated_buildings(self, new_objects: dict[int, list]):
        # This function might not translate well to cpp, and it's
        # goal is to remove isolated buildings from the world.
        # Cpp might have a better way to handle this
        if len(new_objects) == 0:
            return
        for tube in new_objects.get(T_TUBE, []):
            self.isolated_pads.discard(tube.b1)
            self.isolated_pads.discard(tube.b2)
        for tele in new_objects.get(T_TELE, []):
            self.isolated_pads.discard(tele.b1)
            self.isolated_pads.discard(tele.b2)

    def bill(self, amount, msg=""):
        self.resources -= amount
        if LOGGING_PARSING:
            log(f"Billed: {amount}, Remaining: {self.resources}, {msg}")

G_MODEL = SimModel()
#################### METHODS ####################

def search_graph(start, target, adjency_list):
    """
    Search for target starting from start in the adjency_list

    Currently it's depth-first search since it's recursive
    This is because I am an idiot and I don't know how to implement a queue in python
    """
    def recursive_magic_inner(current, target, adjency_list, visited):
        if current == target:
            return [current]
        visited.add(current)
        for node in adjency_list[current]:
            if node not in visited:
                path = recursive_magic_inner(node, target, adjency_list, visited)
                if path:
                    return [current] + path
        return None
    visited = set()
    path = recursive_magic_inner(start, target, adjency_list, visited)
    if path is None:
        return []
    return path

def merge_cities(city1, city2, link_building_1, link_building_2, link, model=G_MODEL):
    """
    When conecting two buildings from different cities, we need to merge the cities
    Take one city as a reference (the larger one) to modify in-place and return it
    """
    # Take the larger one as reference to reduce the merge cost
    tmp = city1
    if len(city1.buildings_ids) + len(city1.tubes) < len(city2.buildings_ids) + len(city2.tubes):
        city1 = city2
        city2 = tmp

    ### If a merge makes no sense, return None
    if link_building_1.city != city1 or link_building_2.city != city2:
        return None
    if link_building_1.city == link_building_2.city:
        return None
    if city1 == city2:
        return None

    city1.buildings_ids = city1.buildings_ids.union(city2.buildings_ids)
    for pad in city2.landing_pads.values():
        pad.city = city1
    for hangout in city2.hangouts.values():
        hangout.city = city1

    for tube in city2.tubes.values():
        tube.city = city1
    for tp in city2.teleporters.values():
        tp.city = city1

    city1.landing_pads.update(city2.landing_pads)
    city1.hangouts.update(city2.hangouts)
    city1.tubes.update(city2.tubes)

    city1.teleporters.update(city2.teleporters)
    city1.pods.update(city2.pods)

    city1.adjency_list.update(city2.adjency_list)
    city1.adjency_list[link_building_1].append(link_building_2)
    city1.adjency_list[link_building_2].append(link_building_1)
    for key in city2.dudes:
        city1.dudes[key] = city1.dudes.get(key, 0) + city2.dudes[key]
    city1.add_link(link) # Finally add the new link
    model.cities.remove(city2)
    return city1

def get_closest_city_building(start_building, model=G_MODEL):
    """
    Get the closest city-building to a building
    """
    closest_dist = 9999
    closest_building = None
    for b in model.buildings.values():
        if b.city is not None:
            dist = start_building.pos.distance(b.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_building = b
    return closest_building

def get_closest_stray_hangout(start_building, model=G_MODEL):
    """
    Get the closest hangout to a start_building
    """
    closest_dist = 9999
    closest_hangout = None
    for hangout in model.isolated_hangouts:
        dist = start_building.pos.distance(hangout.pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_hangout = hangout
    return closest_hangout

###################################
# ███    ███  █████  ██ ███    ██ #
# ████  ████ ██   ██ ██ ████   ██ #
# ██ ████ ██ ███████ ██ ██ ██  ██ #
# ██  ██  ██ ██   ██ ██ ██  ██ ██ #
# ██      ██ ██   ██ ██ ██   ████ #
###################################

def put_stray_pads_in_cities_or_create_new_cities(model):
    """
    Put stray landing pads in cities or create new cities
    new_objects is a dictionary of the new objects created:
        - {city: [new_cities],
        - {tube: [new_tubes],
        - {teleporter: [new_teleporters]}
    """
    all_new_objects = {}
    for pad in model.isolated_pads:
        closest_city = get_closest_city_building(pad, model)
        closest_stray_hangout = get_closest_stray_hangout(pad, model)

        if closest_city is None and closest_stray_hangout is None:
            log(f"Error: No city or hangout in the world")
            return all_new_objects

        # For new outer-city links, we favor tubes over teleporters
        if closest_city is None:
            other_id = closest_stray_hangout.id
            new_objects = conect_buildings(pad, closest_stray_hangout, model, type=T_TUBE)
        elif closest_stray_hangout is None:
            other_id = closest_city.id
            new_objects = conect_buildings(pad, closest_city, model, type=T_TUBE)
        else:
            # Later, compute which link is the best, for now we just connect to the closest
            closest_pos = get_closest_point(pad.pos, closest_city.pos, closest_stray_hangout.pos)
            closest = closest_city if closest_pos == closest_city.pos else closest_stray_hangout
            other_id = closest.id
            new_objects = conect_buildings(pad, closest, model, type=T_TUBE)
        if isinstance(new_objects, int): # Error status
            log(f"Conecting {pad.id} & {other_id}: {error_strings.get(new_objects), 'Error'}")
        else:
            update_dict_lists(all_new_objects, new_objects)
    return all_new_objects

def get_all_new_unused_tubes(new_objects):
    """
    Return:
     - A list of unused new links
    """
    if new_objects is None or len(new_objects) == 0:
        return [], 0
    tubes = new_objects.get(T_TUBE, [])
    # The number of separated new routes
    visited_cities = set()
    for tube in tubes:
        visited_cities.add(tube.b1.city)
    return tubes, len(visited_cities)

def check_stray_hangouts_and_see_if_you_could_add_them_in_cities(model: SimModel, money_to_keep):
    all_new_objects = {}
    for stray in model.isolated_hangouts:
        closest_city_building = get_closest_city_building(stray, model)
        if closest_city_building is None: # No landing pads in the whole world
            return all_new_objects, NOTHING_TO_DO
        if model.resources - TUBE_PRICE * stray.pos.distance(closest_city_building.pos) < money_to_keep:
            return all_new_objects, NO_FUNDS
        new_objects = conect_buildings(stray, closest_city_building, model, type=T_TUBE)
        if isinstance(new_objects, int):
            return all_new_objects, new_objects
        for key, val in new_objects.items():
            all_new_objects.get(key, []).extend(val)
    return all_new_objects, SUCCESS

def create_or_update_routes(model, unused_new_tubes, min_pods):
    """
    For any new unused tubes, create a pod to serve them
    """
    # Rudimentary way to create pods for new unused tubes
    for tube in unused_new_tubes:
        tpl = (tube.b1.id, tube.b2.id) if tube.b1.building_class == BuildingClass.PAD else (tube.b2.id, tube.b1.id)
        src = tpl[0]
        dest = tpl[1]
        route = [src, dest, src]
        ret = create_pod(tube.city, route)
        if isinstance(ret, int):
            log(f"Error: {error_strings.get(ret)}")
            model.dead_tubes[tube.id] = tube
            continue
        pod = ret[1] # (cost, pod)
        if tube in model.dead_tubes:
            model.dead_tubes.pop(tube.id)
        model.bill(1000, msg="Creating pod")
        model.pods[pod.id] = pod
        pod.announce()

def semi_optimal_algo(model=G_MODEL):
    """
    Semi-optimal cuz I'm only human after all, Don't put the blame on me 🎵
    """
    create_or_update_routes(model, model.dead_tubes.values(), 0)


    all_new_objects = put_stray_pads_in_cities_or_create_new_cities(model)
    log(f"New objects: {all_new_objects}")
    model.clean_isolated_buildings(all_new_objects)

    unused_new_tubes, min_pods = get_all_new_unused_tubes(all_new_objects)
    log(f"Unused new tubes: {unused_new_tubes}, Min pods: {min_pods}")

    new_objects, status = check_stray_hangouts_and_see_if_you_could_add_them_in_cities(model, min_pods * POD_PRICE)
    if status != SUCCESS:
        log(f"Error: {error_strings.get(status)}")
    else:
        log(f"New objects: {new_objects}")
    model.clean_isolated_buildings(new_objects)
    all_new_objects = update_dict_lists(all_new_objects, new_objects)

    # maybe_merge_cities_if_it_helps_balance_or_speed(model)
    unused_new_tubes, min_pods = get_all_new_unused_tubes(all_new_objects)
    create_or_update_routes(model, unused_new_tubes, min_pods)
    pass

###################################
# Game loop
while True:
    start_time = time.time()
    G_MODEL.parse_input() # Parse the input and performs other initializations
    semi_optimal_algo(G_MODEL) # The semi-optimal algorithm

    log(f"Time: {int((time.time() - start_time) * 1000)} ms")
    close_round()
