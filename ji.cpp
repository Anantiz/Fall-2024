#include <chrono>
#include <iterator>
#include <vector>
#include <map>
#include <list>
#include <queue>
#include <deque>
#include <set>
#include <algorithm>
#include <cmath>
#include <string>
#include <iostream>
#include <sstream>
#include <tuple>
#include <functional> // For std::hash

#define LOGGING_PARSING true
#define EPSILON 0.00001
#define POD_PRICE 1000
#define TUBE_PRICE 10
#define TELEPORTER_PRICE 5000

#define NOTHING_TO_DO 1
#define SUCCESS 0
#define STANDARD_ERROR -1
#define NO_FUNDS -2
#define GEOMETRIC_IMPOSSIBLE -3
#define NO_CAPACITY -4
#define SUB_OPTIMAL -5

#define T_TUBE 1
#define T_TELE 2
#define T_CITY 3
#define T_PODS 4

class SimModel;
class City;

class Building;
class LandingPad;
class Hangout;

class Link;
class Pod;
class Tube;
class Teleporter;

// ██    ██ ████████ ██ ██      ███████
// ██    ██    ██    ██ ██      ██
// ██    ██    ██    ██ ██      ███████
// ██    ██    ██    ██ ██           ██
//  ██████     ██    ██ ███████ ███████

class Flow
{
    /**
     * We can see our problem as flood managment, where
     * Dudes are water, and cities are drainage bassin
     * We have 20 different types of liquids and bassin
     * We need to balance these types (that cannot mix)
     * And too balance the overall quantity
     */
public:

    std::map<float, float>    data;

    Flow() {}

    Flow(int type) {
        data[type] = -1.0;
    }

    Flow(const std::vector<int>& new_data, int skip)
    {
        for (auto dude_types = new_data.begin() + skip; dude_types != new_data.end(); ++dude_types)
        {
            int dude_type = *dude_types;
            if (data.find(dude_type) == data.end())
                data[dude_type] = 1.0;
            else
                data[dude_type] += 1.0;
        }
    }

    Flow(const std::vector<int>& new_data)
    {
        for (auto dude_types = new_data.begin(); dude_types != new_data.end(); ++dude_types)
        {
            int dude_type = *dude_types;
            if (data.find(dude_type) == data.end())
                data[dude_type] = 1.0;
            else
                data[dude_type] += 1.0;
        }
    }

    Flow &operator+(const Flow& other)
    {
        for (const auto& [type, count]: other.data ) {
            if (data.find(type) != data.end())
                data[type] += count;
            else
                data[type] = count;
        }
        return *this;
    }

    Flow &operator+=(const Flow& other) {
        for (const auto& [type, count]: other.data ) {
            if (data.find(type) != data.end())
                data[type] += count;
            else
                data[type] = count;
        }
        return *this;
    }

    Flow &operator=(const Flow& other) {
        data = other.data;
        return *this;
    }

    int get_type_count(int type) const {
        auto it = data.find(type);
        if (it == data.end())
            return 0;
        return (*it).second;
    }

    std::string to_string( void ) const
    {
        std::string result = " dudes={";
        for (const auto& pair : data) {
            result += std::to_string(pair.first) + ": " + std::to_string(pair.second) + ", ";
        }
        result.pop_back(); result.pop_back();  // Remove last ", "
        result += "}";
        return result;
    }

    static Flow get_overflow(const Flow& source, const std::map<int, int> &hangouts_type)
    {
        Flow overflow = source;

        for (const auto& [type, count]: hangouts_type) {
            if (overflow.data.find(type) == overflow.data.end()) {
                overflow.data[type] = -count; // Actually an underflow
            } else {
                // Put a ratio of In-flow over Out-flow
                // Add 10,000 as magic value (Natural values will never be that high)
                // So we can later catch these large values and know they are balance-ratios and not an overflow
                if (count != 0)
                    overflow.data[type] = (overflow.data[type]) + 10000;
            }
        }
        return overflow;
    }
};

void log(const std::string& message) {
    std::cerr << message << std::endl;
}

const std::string &error_strings(int e) {
    static std::map<int, std::string> error_strings;

    if (error_strings.size() == 0) {
        error_strings[NOTHING_TO_DO] = "Nothing to do";
        error_strings[SUCCESS] = "Success";
        error_strings[STANDARD_ERROR] = "Standard error";
        error_strings[NO_FUNDS] = "Not enough funds";
        error_strings[GEOMETRIC_IMPOSSIBLE] = "Geometrically impossible";
        error_strings[NO_CAPACITY] = "No capacity";
    }
    auto it = error_strings.find(e);
    if (it == error_strings.end())
        return error_strings[STANDARD_ERROR];
    return it->second;
}

template <typename T>
inline void hash_combine(std::size_t& seed, const T& value) {
    seed ^= std::hash<T>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

// Specialize std::hash for std::tuple<int, int>
namespace std {
    template<>
    struct hash<std::tuple<int, int>> {
        std::size_t operator()(const std::tuple<int, int>& t) const {
            std::size_t seed = 0;
            hash_combine(seed, std::get<0>(t)); // hash x
            hash_combine(seed, std::get<1>(t)); // hash y
            return seed;
        }
    };
}

class Point {
public:
    int x, y;

    Point(int x, int y) : x(x), y(y) {}

    double distance(const Point& point) const {
        return std::sqrt(std::pow(x - point.x, 2) + std::pow(y - point.y, 2));
    }

    // Overload the +, -, *, /, and // operators
    Point operator+(const Point& point) const { return Point(x + point.x, y + point.y); }
    Point operator-(const Point& point) const { return Point(x - point.x, y - point.y); }
    Point operator*(const Point& point) const { return Point(x * point.x, y * point.y); }
    Point operator/(const Point& point) const { return Point(x / point.x, y / point.y); }
    bool operator==(const Point& point) const { return x == point.x && y == point.y; }
    friend std::ostream& operator<<(std::ostream& os, const Point& point) {
        os << "(" << point.x << ", " << point.y << ")";
        return os;
    }
    // Hash function
    std::size_t hash() const {
        return std::hash<std::tuple<int, int>>{}(std::make_tuple(x, y));
    }
};

void print_action_tube(int building_id1, int building_id2) {
    std::cout << "TUBE " << building_id1 << " " << building_id2 << ";";
}
void print_action_upgrade_tube(int building_id1, int building_id2) {
    std::cout << "UPGRADE " << building_id1 << " " << building_id2 << ";";
}
void print_action_teleport(int building_entrance_id, int building_ausgang_id) {
    std::cout << "TELEPORT " << building_entrance_id << " " << building_ausgang_id << ";";
}
void print_action_pod(int pod_id, const std::vector<int>& path_building_ids) {
    std::cout << "POD " << pod_id;
    for (const auto& building_id : path_building_ids) {
        std::cout << " " << building_id;
    }
    std::cout << ";";
}
void print_action_destroy(int pod_id) {
    std::cout << "DESTROY " << pod_id << ";";
}
void close_round() {
    // newline in stdout ends the round
    // Wait is a placeholder for rounds where no action is needed (Ignored if there is any other action)
    std::cout << "WAIT" << std::endl;
}

enum TeleporterState { Frei, Eingang, Ausgang };
enum BuildingClass { PAD, HANGOUT };

/****** CITY *******/
class City {
public:
    std::set<int>                   buildings_ids;  // Set of building IDs
    std::map<int, LandingPad*>      landing_pads;  // Mapping ID to LandingPad
    std::map<int, Hangout*>         hangouts;  // Mapping ID to Hangout
    std::map<int, Link*>            tubes;  // Mapping ID to Tube
    std::map<int, Link*>            teleporters;  // Mapping ID to Teleporter
    std::map<int, Pod*>             pods;  // Mapping ID to Pod
    std::map<int, std::vector<int>> adjency_list;  // Adjacency list for buildings
    Flow                            dudes;  // City dude register {dude_type: population}
    std::map<int, int>              hangouts_types;

    // Constructor
    City(LandingPad* pad, Hangout* hangout, Link* link);
    ~City() {}

    // Graph pathfinding function (BFS as an example)
    std::vector<int> graph_find_path(Building* A, Building* B) const;

    void    add_building(Building* building);
    void    add_link(Link* link);
    void    add_pod(Pod* pod);
    void    merge_city(const City& other);

    int has_type_outflow(int type) const;
    int has_type_inflow(int type) const;
};



// ██████  ██    ██ ██      ██████  ██ ███    ██  ██████
// ██   ██ ██    ██ ██      ██   ██ ██ ████   ██ ██
// ██████  ██    ██ ██      ██   ██ ██ ██ ██  ██ ██   ███
// ██   ██ ██    ██ ██      ██   ██ ██ ██  ██ ██ ██    ██
// ██████   ██████  ███████ ██████  ██ ██   ████  ██████

class Building {
private:

    Building();

public:
    int                     id, x, y, type;
    enum BuildingClass      building_class;
    enum TeleporterState    tp_state;
    Point                   pos;
    City*                   city;  // Pointer to City class
    Building*               tp_with;

    // Placeholder to return an empty vector
    static const std::vector<int> empty_vector;

    Building(BuildingClass building_class, int type, int x, int y, int id)
        : building_class(building_class), type(type), x(x), y(y), id(id), pos(x, y), tp_state(TeleporterState::Frei), tp_with(nullptr), city(nullptr) {}
    virtual ~Building() {}

    const std::vector<int> &get_adjacents() const
    {
        if (city == nullptr)
            return empty_vector;  // Return an empty vector if city is null
        else
            return city->adjency_list[id];  // Assuming adjency_list is defined in City
    }

    const Point &get_pos() const {
        return pos;
    }

    virtual std::string to_string() const = 0;
};
const std::vector<int> Building::empty_vector = std::vector<int>();

class LandingPad : public Building {
public:
    Flow dudes;

    LandingPad(int x, int y, int id)
        : Building(BuildingClass::PAD, 0, x, y, id) {}

    std::string to_string() const {
        std::string result = "Lunar pad: id=" + std::to_string(id) + " pos=" + "(" + std::to_string(x) \
        + ", " + std::to_string(y) + ")" + dudes.to_string();
        return result;
    }

    void set_dudes(const std::vector<int> &data, int skip) {
        dudes = Flow(data, skip);
    }

    const Flow& get_dudes() const {
        return dudes;  // Return a reference to dudes
    }
};

class Hangout : public Building {
public:
    Hangout(int type, int x, int y, int id)
        : Building(BuildingClass::HANGOUT, type, x, y, id) {}

    std::string to_string() const {
        return "Hangout: id=" + std::to_string(id) + " pos=" + "(" + std::to_string(x) + ", " + std::to_string(y) + ")" + " type=" + std::to_string(type);
    }
};



// ██      ██ ███    ██ ██   ██ ███████
// ██      ██ ████   ██ ██  ██  ██
// ██      ██ ██ ██  ██ █████   ███████
// ██      ██ ██  ██ ██ ██  ██       ██
// ███████ ██ ██   ████ ██   ██ ███████

class Link {
public:
    int         id;
    int         capacity;
    // Pointers to Buildings
    Building*   b1;
    Building*   b2;
    City*       city;

    Link(Building* b1, Building* b2, int id, int capacity)
    : b1(b1), b2(b2), id(id), capacity(capacity) {
        city = b1->city;  // Assuming b1 and b2 belong to the same city
    }
    virtual ~Link() {}

    bool upgrade() {
        if (capacity == 0 || capacity == 3)
            return false;
        capacity += 1;
        return true;
    }
};

class Tube : public Link {
    static int tube_id_gen;
public:

    Tube(Building* b1, Building* b2)
    : Link(b1, b2, tube_id_gen++, 1) {

    }
};

int Tube::tube_id_gen = 0;

class Teleporter : public Link {
    static int tp_id_gen;
public:

    Teleporter(Building* b1, Building* b2)
    : Link(b1, b2, tp_id_gen++, 0) {
        b1->tp_state = TeleporterState::Eingang;  // Assuming enum exists
        b2->tp_state = TeleporterState::Ausgang;
    }
};

int Teleporter::tp_id_gen = 0;

class Pod {
private:
    static int pod_id_gen;
public:
    int id;
    Pod() : id(pod_id_gen) {pod_id_gen++;}
};

int Pod::pod_id_gen = 0;


//  ██████ ██ ████████ ██    ██
// ██      ██    ██     ██  ██
// ██      ██    ██      ████
// ██      ██    ██       ██
//  ██████ ██    ██       ██

std::vector<int> City::graph_find_path(Building* A, Building* B) const
{
    if (buildings_ids.find(A->id) == buildings_ids.end() \
    or buildings_ids.find(B->id) == buildings_ids.end()) {
        return {};  // Return an empty vector if A or B not in city
    }
    if (A->id == B->id)
        return {A->id};  // Return a single-element vector if A == B

    // Perform BFS for shortest path
    std::map<int, int> prev;  // To track the path
    std::queue<int> q;
    q.push(A->id);
    prev[A->id] = -1;

    while (!q.empty()) {
        int current = q.front();
        q.pop();
        for (auto neighbor : adjency_list.at(current)) {
            if (prev.find(neighbor) == prev.end()) {  // Not visited
                prev[neighbor] = current;
                q.push(neighbor);
                if (neighbor == B->id) {  // Found B
                    std::vector<int> path;
                    for (int at = B->id; at != -1; at = prev[at]) {
                        path.push_back(at);
                    }
                    std::reverse(path.begin(), path.end());
                    return path;  // Return the path from A to B
                }
            }
        }
    }
    return {};  // No path found
}

// Add a building to the city
void City::add_building(Building* building)
{
    buildings_ids.insert(building->id);
    building->city = this;

    if (adjency_list.find(building->id) == adjency_list.end())
        adjency_list[building->id] = {};  // Initialize adjacency list for the building

    if (building->building_class == BuildingClass::HANGOUT)
    {
        hangouts[building->id] = dynamic_cast<Hangout*>(building);

        if (hangouts_types.find(building->type) == hangouts_types.end())
            hangouts_types[building->type] = 1;
        else
            hangouts_types[building->type] += 1;
    } else if (building->building_class == BuildingClass::PAD)
    {
        landing_pads[building->id] = dynamic_cast<LandingPad*>(building);
        // Add dudes to the city's dude register
        this->dudes += dynamic_cast<LandingPad*>(building)->get_dudes();
    }
}

// Add a link (tube or teleporter)
void City::add_link(Link* link) {
    link->city = this;

    adjency_list[link->b1->id].push_back(link->b2->id);
    adjency_list[link->b2->id].push_back(link->b1->id);

    if (link->capacity == 0)
        teleporters[link->id] = link;  // Add to teleporters if capacity is 0 (unlimited)
    else
        tubes[link->id] = link;  // Add to tubes otherwise
}

// Add a pod to the city
void City::add_pod(Pod* pod) {
    pods[pod->id] = pod;
}

void City::merge_city(const City& other)
{
    for (const auto& [id, building] : other.landing_pads) {
        add_building(building);
    }
    for (const auto& [id, building] : other.hangouts) {
        add_building(building);
    }
    for (const auto& [id, link] : other.tubes) {
        add_link(link);
    }
    for (const auto& [id, link] : other.teleporters) {
        add_link(link);
    }
    for (const auto& [id, pod] : other.pods) {
        add_pod(pod);
    }
    this->dudes = this->dudes + other.dudes;
}

int City::has_type_outflow(int type) const {
    auto it = hangouts_types.find(type);
    if (it == hangouts_types.end())
        return 0;
    return (*it).second;
}

int City::has_type_inflow(int type) const {
    return dudes.get_type_count(type);
}

// ███    ███  ██████  ██████  ███████ ██
// ████  ████ ██    ██ ██   ██ ██      ██
// ██ ████ ██ ██    ██ ██   ██ █████   ██
// ██  ██  ██ ██    ██ ██   ██ ██      ██
// ██      ██  ██████  ██████  ███████ ███████

class UniqueFIFOQueue {
    // Implementing a unique FIFO queue, similar to what you have in Python
    std::queue<int> queue;
    std::set<int> unique_set;

public:
    void push(int element) {
        if (unique_set.find(element) == unique_set.end()) {
            queue.push(element);
            unique_set.insert(element);
        }
    }

    int pop() {
        if (!queue.empty()) {
            int front = queue.front();
            queue.pop();
            unique_set.erase(front);
            return front;
        }
        return -1; // Return -1 if queue is empty
    }

    bool empty() const {
        return queue.empty();
    }
};

class SimModel {
public:
    int round;
    int resources;
    UniqueFIFOQueue action_queue; // Queue to store available actions, if needed later
    std::vector<City*> cities;

    // Buildings
    std::set<int> isolated_hangouts;
    std::set<int> isolated_pads;
    std::map<int, Building*> buildings; // {id: Building*}

    // Routes
    std::map<int, std::vector<std::pair<int, int>>> routes; // {id: {neighbor_id, capacity}}
    std::map<int, Tube*> tubes;  // {id: Tube*}
    std::map<int, Teleporter*> teleporters; // {id: Teleporter*}
    std::map<int, Pod*> pods; // {id: Pod*}
    std::map<int, Tube*> dead_tubes; // Tubes not being used in current routes

    // Constructor
    SimModel() : round(-1), resources(0) {}

    // Parse input method
    void parse_input() {
        round++;
        std::cin >> resources; std::cin.ignore();

        if (LOGGING_PARSING) {
            log("Resources: " + std::to_string(resources));
        }

        int num_travel_routes;
        std::cin >> num_travel_routes; std::cin.ignore();
        for (int i = 0; i < num_travel_routes; ++i) {
            int building_id_1, building_id_2, capacity;
            std::cin >> building_id_1 >> building_id_2 >> capacity; std::cin.ignore();

            routes[building_id_1].emplace_back(building_id_2, capacity);
            routes[building_id_2].emplace_back(building_id_1, capacity);
        }

        int num_pods;
        std::cin >> num_pods; std::cin.ignore();
        for (int i = 0; i < num_pods; i++) {
            std::string pod_properties;
            std::getline(std::cin, pod_properties);
            if (LOGGING_PARSING) {
                log("Pod properties: " + pod_properties);
            }
        }

        int num_new_buildings;
        std::cin >> num_new_buildings; std::cin.ignore();

        for (int i = 0; i < num_new_buildings; ++i) {
            std::string building_properties;
            std::getline(std::cin, building_properties);

            std::istringstream ss(building_properties);
            std::vector<int> data((std::istream_iterator<int>(ss)), std::istream_iterator<int>());

            if (data[0] == 0) {
                // LandingPad
                buildings[data[1]] = new LandingPad(data[2], data[3], data[1]);
                dynamic_cast<LandingPad*>(buildings[data[1]])->set_dudes(data, 5);
                isolated_pads.insert(data[1]);
            } else {
                // Hangout
                buildings[data[1]] = new Hangout(data[0], data[2], data[3], data[1]);
                isolated_hangouts.insert(data[1]);
            }

            if (LOGGING_PARSING) {
                log(buildings[data[1]]->to_string());
            }
        }

        if (LOGGING_PARSING) {
            log("New buildings: " + std::to_string(num_new_buildings));
        }
    }

    // Clean isolated buildings
    void clean_isolated_buildings(const std::map<int, std::vector<Tube*>>& new_objects) {
        if (new_objects.empty()) return;

        for (const auto& tube : new_objects.at(T_TUBE)) {
            isolated_pads.erase(tube->b1->id);
            isolated_pads.erase(tube->b2->id);
        }
        for (const auto& tele : new_objects.at(T_TELE)) {
            isolated_pads.erase(tele->b1->id);
            isolated_pads.erase(tele->b2->id);
        }
    }

    // Billing method
    void bill(int amount, const std::string& msg = "") {
        resources -= amount;

        if (LOGGING_PARSING) {
            log("Billed: " + std::to_string(amount) + ", Remaining: " + std::to_string(resources) + ", " + msg);
        }
    }
};

// ██████  ██    ██ ████████ ██   ██ ███    ███
// ██   ██  ██  ██     ██    ██   ██ ████  ████
// ██████    ████      ██    ███████ ██ ████ ██
// ██   ██    ██       ██    ██   ██ ██  ██  ██
// ██   ██    ██       ██    ██   ██ ██      ██


typedef std::vector<std::tuple<City*, LandingPad*, Flow> > t_sources;
typedef std::vector< std::tuple<City*, Hangout*, Flow> >  t_drains;

// Pair: [Sources:(City or Pad)], [Drains:(City or Hangout)]
typedef std::pair<t_sources, t_drains> t_DudeSupplyChain;
typedef std::vector<std::tuple<int, int, int> > t_actions;
typedef std::vector<int> t_route;


/**
 * A city is both a source and a drain of dudes
 * A stray pad is always a source of dudes
 * A stray hangout is always a drain of dudes
 *
 * Hangouts have unlimited capacity, but the more dudes they have per round, the less score they give (unbalanced flow)
 *
 */
t_DudeSupplyChain check_dude_supply_chain(SimModel &model)
{
    t_DudeSupplyChain supply_chain;
    t_sources &sources = supply_chain.first;
    t_drains &drains = supply_chain.second;

    // Ratios
    for (const auto& city : model.cities) {
        sources.push_back(std::make_tuple(city, nullptr, Flow::get_overflow(city->dudes, city->hangouts_types)));
        drains.push_back(std::make_tuple(city, nullptr, Flow::get_overflow(city->dudes, city->hangouts_types)));
    }
    // Sources
    for (const auto& id : model.isolated_pads) {
        sources.push_back(std::make_tuple(nullptr, \
        dynamic_cast<LandingPad*>(model.buildings[id]), dynamic_cast<LandingPad*>(model.buildings[id])->dudes));
    }
    // Drains
    for (const auto& id : model.isolated_hangouts) {
        drains.push_back(std::make_tuple(nullptr, \
        dynamic_cast<Hangout*>(model.buildings[id]), Flow(model.buildings[id]->type)));
    }
    return supply_chain;
}

t_actions    suggest_links_for_supply_chain(SimModel &model, t_DudeSupplyChain &supply_chain)
/*
Takes the supply chain and suggest new links in order of priority
The links that will balance the flow the most will be the first to be suggested
*/
{
    /*
    Layer 1: Identify "critical" links that should be built independently. These are the most obvious supply-demand connections that are clearly necessary.
    Layer 2: Once critical links are made, identify dependent links that only make sense after the first layer has been established.
    Layer 3: For each dependent link, evaluate whether its impact justifies the cost and complexity.
    */

    // building_id1, building_id2, link_type(T_TUBE or T_TELE)
    t_actions available_new_links;

    /*
        loop:
            find_largest_source:
                find_all_fitting_drains
                for_fitting_drains_sort_by_balance (Stray hanoguts will bring more balance than a city which already has src/drain)
            redo_with_next_largest_source

        loop:
            for_each_city:
                check_sources_with_no_drains
                match_the_best_drains (might be an other city, or a stray hangout)

        TO-DO: Later, find the longest distance between a source and drain in the same city and connect them
    */

    return available_new_links;
}

std::vector<std::pair<t_route, t_actions> > check_routes(SimModel &model, t_DudeSupplyChain &supply_chain, t_actions &suggested_links)
/*
Considering any links that could be built, and existing links, defines the best routes for the dudes
*/
{
    // [ pair([route], links_required), ... ]
    std::vector<std::pair<t_route, t_actions> > \
    new_routes_if_links_are_built;


    return new_routes_if_links_are_built;
}

void do_best_decision(SimModel &model, std::vector<std::pair<t_route, t_actions> > &potential_new_routes)
{
    (void) model;
    (void) potential_new_routes;
    // For all routes, takes the one that do not interfere, and keep them in budget
}

/**
 * Semi-Optimal Algorithm
 *  > Because it is NP-Hard, and we are bound to 500ms per turn (1000ms for the first turn)
 *  > I am only human after all, don't put the blame on me, don't put the blame on me.
 *
 * */
void semi_optimal_algorithm(SimModel& model)
/*
First, check if there are isolated hangouts or pads.
    If there are, check how you would connect them if you had to
    (Store this different conections in a vector) vec<b1, b2, link_type>
Then, for every two cities:
    check if there is an over-supply of dudes in one city as compared to the other
    (Take the type of the dudes into account, otherwise this step is useless)
    Then have again a vector of actions vec<b1, b2, link_type
Lastly: Most Critical part to get right
    Have a Route manager, it is an algorithm that will:
        - Consider the supply of dudes in each city, and for each pad (source of dudes)
        - Consider the current existing network of links (tubes and teleporters) and how these dudes could best flow in the network
        - With this "potential" flow, see how new links could influence it for better or worse
        - Last step: Find the balance between spending new-links and setting routes for the dudes
    The Routes: Core of all of this:
        - The routes are either fixed (Teleporters) or dynamic (Tubes)
        - Tubes are dynamic because the only move dudes around when a pod does the trip
        - Pods have a maximum number of dudes they can carry, and tubes have a maximum of pods they can carry
        - Pods need to make round-trips (or they will stop once they reach the end of the route)
        - Pods can be moved around (Destroy+Rebuild) for a cost of 250, this is crucial to consider because:
            - New links will need to have pods serving them, and pods are like, expensive, so a pod should be used as much as possible
            - But not too much otherwise it will be too slow, and dudes give less score if it takes too long to reach their destination
*/
{
    auto dude_supply_chain = check_dude_supply_chain(model);
    auto suggested_links = suggest_links_for_supply_chain(model, dude_supply_chain);
    auto potential_new_routes = check_routes(model, dude_supply_chain, suggested_links);;

    do_best_decision(model, potential_new_routes);
}


//  ███    ███  █████  ██ ███    ██
//  ████  ████ ██   ██ ██ ████   ██
//  ██ ████ ██ ███████ ██ ██ ██  ██
//  ██  ██  ██ ██   ██ ██ ██  ██ ██
//  ██      ██ ██   ██ ██ ██   ████

int main() {

    SimModel model;

    while (true) {
        auto start = std::chrono::system_clock::now();
        model.parse_input();
        semi_optimal_algorithm(model);
        close_round();
        std::chrono::duration<double> elapsed = std::chrono::system_clock::now() - start;
        auto milliseconds = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();
        log("Elapsed time: " + std::to_string(elapsed.count()) + " ms");
    }
    return 0;
}