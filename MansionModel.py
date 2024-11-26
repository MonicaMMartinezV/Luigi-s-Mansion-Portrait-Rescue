from mesa import Model  # Define los agentes y el modelo base de la simulación
from mesa.space import MultiGrid  # Permite colocar los agentes en una cuadrícula (multi o individual)
from mesa.time import BaseScheduler
from mesa.datacollection import DataCollector  # Recolecta y organiza datos de la simulación para análisis
from LuigiAgent import LuigiAgent

# Librerías matemáticas y generación de aleatoriedad
import itertools  # Proporciona herramientas para crear combinaciones y permutaciones
import random  # Permite generar números y secuencias aleatorias, útil para la variabilidad en simulaciones
import math  # Contiene funciones matemáticas básicas, como operaciones trigonométricas y logarítmicas

class MansionModel(Model):
    def __init__(self, luigis, fake_alarms,
                 victims, walls, doors, boo, 
                 entrances, mode, seed):
        # Inicializar la clase base Model sin argumentos adicionales
        
        super().__init__()

        print(f"Seed: {seed}")
        random.seed(seed)

        # Variables iniciales del modelo
        self.step_count        = 0
        self.schedule          = BaseScheduler(self)  # Usamos BaseScheduler para compatibilidad futura
        self.rescued           = 0
        self.losses            = 0
        self.casualties        = 0
        #self.saved_count      = 0
        self.simulation_status = "In progress"
        self.boo_zones         = [(row, col) for col, row in boo]
        self.wall_config       = walls
        self.mode              = mode
        self.model_events = []

        # Configuración del recolector de datos
        self.datacollector = DataCollector(
            model_reporters={
                "Grid": "get_grid",
                "Walls": "get_walls",
                "Steps": "step_count",
                "Doors": "doors",
                "Damage": "damage_counter",
                "Status": "simulation_status",
                "Portraits": "portraits",
                "Rescued": "rescued",
                "Losses": "losses"
            },
            agent_reporters={
                "Agent_ID": lambda agent: agent.unique_id,
                "Role": lambda agent: agent.role,
                "Position": lambda agent: (agent.pos[0], agent.pos[1]),
                "Agent History": lambda agent: getattr(agent, 'history', [])
            }
        )

        self.portraits = {}
        for (row, col) in fake_alarms:
            self.portraits[(int(col), int(row))] = "false_alarm"
        for (row, col) in victims:
            self.portraits[(int(col), int(row))] = "victim"

        # Imprimir información inicial de retratos
        print("[INFO] Coordenadas iniciales de retratos:")
        for coord, portrait_type in self.portraits.items():
            print(f"  - {coord}: {portrait_type}")

        # Dimensiones del grid
        self.grid_width = 10
        self.grid_height = 8

        # Configuración de puertas y entradas
        self.exit_positions = doors
        self.entrances = [(int(col), int(row)) for row, col in entrances]

        # Imprimir información inicial de puertas y entradas
        print("[INFO] Coordenadas iniciales de entradas:")
        for entrance in self.entrances:
            print(f"  - {entrance}")

        print("[INFO] Coordenadas iniciales de puertas:")
        for door in self.exit_positions:
            print(f"  - {door}")

        def print_grid_coordinates(grid_width, grid_height):
            """Imprime todas las coordenadas posibles del grid en un tablero ASCII."""
            print("\n--- Coordenadas del Grid ---")
            for y in range(grid_height):
                row = ""
                for x in range(grid_width):
                    row += f"({x},{y})".ljust(10)  # Ajustar el ancho de cada celda para alinear
                print(row)
            print("\n")

        # Crear el espacio y los detalles del grid
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        self.grid_details = {(x, y): 0 for y in range(self.grid_height) for x in range(self.grid_width)}
        
        self.damage_counter = 0

        # Imprimir las coordenadas del grid
        print_grid_coordinates(self.grid_width, self.grid_height)

        # Inicializar el grid de muros respetando el rango válido
        self.grid_walls = {
            (x, y): ["0000", "0000"]
            for y in range(1, self.grid_height - 1)
            for x in range(1, self.grid_width - 1)
        }

        # Configurar los muros desde self.wall_config
        for y, row in enumerate(self.wall_config, start=1):  # Inicia en 1 para mapear a la grid
            for x, walls in enumerate(row, start=1):  # Inicia en 1 para mapear a la grid
                # Asegurarse de que la celda está dentro del rango válido
                if (x, y) in self.grid_walls:
                    # Convertir la lista de valores en string, si es necesario
                    wall_value = ''.join(map(str, walls))
                    self.grid_walls[(x, y)][0] = wall_value  # Asignar el valor a la celda

        # Imprimir la configuración final de los muros para verificación
        print("[INFO] Configuración inicial de muros:")
        for coord, walls in sorted(self.grid_walls.items()):  # Ordenar por coordenadas
            print(f"  - Coordenada {coord}: {walls[0]}")


        # Configurar zonas de fantasmas
        for position in self.boo_zones:
            self.grid_details[position] = 2
        
        # Imprimir información inicial de zonas de fantasmas
        print("[INFO] Coordenadas iniciales de zonas de fantasmas:")
        for boo_zone in self.boo_zones:
            print(f"  - {boo_zone}")

        # Ajustar posiciones de agentes para colocarlos justo afuera del grid
        def adjust_position_outside_grid(x, y, grid_width, grid_height):
            # Revisar si la entrada está en un borde y mover fuera del grid
            if y == 1:  # Borde superior
                return (x, 0)
            elif x == 1:  # Borde izquierdo
                return (0, y)
            elif x == grid_width - 2:  # Borde derecho
                return (grid_width-1, y)
            elif y == grid_height - 2:  # Borde inferior
                return (x, grid_height-1)
            return (x, y)  # Si no es un borde, no se ajusta (esto no debería ocurrir)

        # Aplicar la lógica de ajuste dinámico
        agent_cy = itertools.cycle([
            adjust_position_outside_grid(x, y, self.grid_width, self.grid_height) 
            for x, y in self.entrances
        ])

        # Agregar agentes Luigi con roles alternados
        agent_roles = ["rescuer", "firefighter"]
        agent_role_cycle = itertools.cycle(agent_roles)
        for idx in range(luigis):
            position = next(agent_cy)
            role = next(agent_role_cycle)
            agent = LuigiAgent(idx, self, role)
            agent.unique_id = idx
            self.grid.place_agent(agent, position)
            self.schedule.add(agent)
            print(f"Agente {idx} con rol {role} colocado en posición {position}")

    def log_event(self, event):
        """Agrega un evento al registro del modelo."""
        self.model_events.append(event)

    def add_portraits(self):
        """Agrega retratos si hay menos de 3 activos dentro del área central del grid."""
        active_points = sum(1 for portrait in self.portraits.values() if portrait in ["victim", "false_alarm"])
        print(f"[DEBUG] Portraits en el tablero: {active_points}")
        if active_points <= 3:
            needed_points = 3 - active_points
            new_points = 0

            # Definir el área central del grid
            central_area = [
                (x, y) for x in range(1, 9) for y in range(1, 7)
            ]

            while new_points < needed_points:
                candidate_point = random.choice(central_area)
                reduced = False
                if candidate_point not in self.portraits:
                    if self.grid_details.get(candidate_point) in [1, 2]:  # 1 para humo, 2 para fuego
                        # Eliminar fuego o humo y colocar el retrato en su lugar
                        self.grid_details[candidate_point] = 0  # Eliminar humo/fuego
                        reduced = True
                        print(f"[DEBUG] El fuego/humo en {candidate_point} fue removido para poner un retrato.")
                    # Agregar un nuevo retrato (víctima o falsa alarma)
                    portrait_type = "victim" if random.choice([True, False]) else "false_alarm"
                    self.portraits[candidate_point] = portrait_type
                    self.grid_details[candidate_point] = 0
                    new_points += 1
                    print(f"[INFO] Nuevo retrato agregado en {candidate_point}: {portrait_type}")
                    self.log_event({
                        "type": "portrait_added",
                        "position": candidate_point,
                        "portrait_type": portrait_type,
                        "step": self.step_count
                    })
                    if reduced:
                        self.log_event({
                            "type": "fire_removed_to_portrait",
                            "position": candidate_point,
                            "portrait_type": portrait_type,
                            "step": self.step_count
                        })

    def spread_boos(self):
        """Extiende la presencia de fantasmas únicamente dentro del área central del grid."""
        print(f"Damage: {self.damage_counter}")
        # Definir el área central del grid
        central_area = [
            (x, y) for x in range(1, 9) for y in range(1, 7)
        ]

        # Filtrar posiciones afectadas dentro del área central
        affected_positions = [
            pos for pos in central_area if self.grid_details.get(pos) in (0, 1, 2)
        ]
        
        if affected_positions:
            target_pos = random.choice(affected_positions)
            if self.grid_details[target_pos] == 0:
                self.grid_details[target_pos] = 1
                print(f"[INFO] Nuevo humo agregado en {target_pos}")
                self.log_event({
                    "type": "smoke_added",
                    "position": target_pos,
                    "step": self.step_count
                })
            elif self.grid_details[target_pos] == 1:
                self.grid_details[target_pos] = 2
                print(f"[INFO] Nuevo fuego agregado en {target_pos}")
                self.log_event({
                    "type": "fire_to_smoke",
                    "position": target_pos,
                    "step": self.step_count
                })
            elif self.grid_details[target_pos] == 2:
                neighbors = self.grid.get_neighborhood(target_pos, moore=False, include_center=False)
                for neighbor in neighbors:
                    if neighbor in central_area:
                        if self.grid_details.get(neighbor) == 0 or \
                           self.grid_details.get(neighbor) == 1:
                            if self.check_collision_walls_doors(target_pos, neighbor):
                                self.register_damage_walls_doors(target_pos, neighbor)
                            else:
                                self.grid_details[neighbor] = 2
                                self.boo_zones.append(neighbor)
                                if self.grid_details.get(neighbor) == 0:
                                    print(f"[INFO] Nuevo fuego extendido de {target_pos} a {neighbor}")
                                    self.log_event({
                                        "type": "fire_extended",
                                        "from": target_pos,
                                        "to": neighbor,
                                        "step": self.step_count
                                    })
                                if self.grid_details.get(neighbor) == 1:
                                    self.log_event({
                                    "type": "smoke_added",
                                    "position": target_pos,
                                    "step": self.step_count
                                })
                        elif self.grid_details.get(neighbor) == 2:
                            if self.check_collision_walls_doors(target_pos, neighbor):
                                self.register_damage_walls_doors(target_pos, neighbor)
                            else:
                                self.trigger_explosion(target_pos,neighbor)
                        else:
                            pass
                    else:
                        if self.check_collision_walls_doors(target_pos, neighbor):
                            self.register_damage_walls_doors(target_pos, neighbor)
                        else:
                            pass


    def register_damage_walls_doors(self, origin, target):
        """Registra daño en muros o puertas."""
        if origin in self.exit_positions and target in self.exit_positions:
            if self.exit_positions[origin]==False and self.exit_positions[target]==False:
                del self.exit_positions[origin]
                del self.exit_positions[target]
                origin_wall = list(self.grid_walls[origin][0])
                target_wall = list(self.grid_walls[target][0])
                path_org = self.direction(origin, target)
                path_targ = self.direction(target, origin)
                origin_wall[path_org] = "0"
                target_wall[path_targ] = "0"
                self.grid_walls[origin][0] = "".join(origin_wall)
                self.grid_walls[target][0] = "".join(target_wall)
                self.damage_counter += 1
        else:
            central_area = [
                (x, y) for x in range(1, 9) for y in range(1, 7)
            ]
            
            if target in central_area:
                path_org= self.direction(origin, target)
                path_targ= self.direction(target, origin)
                origin_wall = list(self.grid_walls[origin][0])
                target_wall = list(self.grid_walls[target][0])
                origin_counter = list(self.grid_walls[origin][1])
                target_counter = list(self.grid_walls[target][1])
                if origin_counter[path_org]== "1" and target_counter[path_targ]== "1":
                    self.damage_counter += 1
                    origin_wall[path_org]= "0"
                    target_wall[path_targ]= "0"
                    self.grid_walls[origin][0] = ''.join(origin_wall)
                    self.grid_walls[target][0] = ''.join(target_wall)
                    print(f"[INFO] Pared destruida de {origin} a {target}")
                    self.log_event({
                        "type": "wall_destroyed",
                        "position": origin,
                        "target": target,
                        "step": self.step_count
                    })
                elif origin_counter[path_org]== "0" and target_counter[path_targ]== "0":
                    self.damage_counter += 1
                    origin_counter[path_org] = "1"
                    target_counter[path_targ] = "1"
                    self.grid_walls[origin][1] = ''.join(origin_counter)
                    self.grid_walls[target][1] = ''.join(target_counter)
                    print(f"[INFO] Daño registrado en {origin} y {target}")
                    self.log_event({
                        "type": "damage_door",
                        "position": origin,
                        "target":target,
                        "step": self.step_count
                    })
                else:
                    pass
            else:
                direction = self.direction(origin, target)
                origin_nw_crnr = (1,1)
                origin_ne_crnr = (8,1)
                origin_sw_crnr = (1,6)
                origin_sw_crnr = (8,6)
                
                if origin == origin_nw_crnr or origin == origin_ne_crnr:
                    if direction != 0:
                        self.wall_damage(origin, target)
                elif origin == origin_sw_crnr or origin == origin_ne_crnr:
                    if direction != 2:
                        self.wall_damage(origin, target)
                elif origin not in self.entrances and \
                   target not in self.entrances:
                    self.wall_damage(origin, target)
    
    def wall_damage(self, origin, target):
        path_org       = self.direction(origin, target)
        origin_wall    = list(self.grid_walls[origin][0])
        origin_counter = list(self.grid_walls[origin][1])
        if origin_counter[path_org]== "1":
            self.damage_counter += 1
            origin_wall[path_org]= "0"
            self.grid_walls[origin][0] = ''.join(origin_wall)
            print(f"[INFO] Pared destruida de {origin} a {target}")
            self.log_event({
                "type": "wall_destroyed",
                "from": origin,
                "to": target,
                "step": self.step_count
            })
        elif origin_counter[path_org]== "0":
            self.damage_counter += 1
            origin_counter[path_org] = "1"
            self.grid_walls[origin][1] = ''.join(origin_counter)
            print(f"[INFO] Daño registrado en {origin}")
            self.log_event({
                "type": "damage_wall",
                "position": origin,
                "step": self.step_count
            })
        else:
            pass

    def trigger_explosion(self, origin, target):
        """
        Maneja la dinámica de explosiones desde una celda específica.
        Las explosiones dañan paredes, se propagan a celdas vecinas y pueden causar daño estructural.
        """
        print(f"[DEBUG] Explosión iniciada en {origin} con dirección a {target}.")
        
        direction = self.direction(origin, target)

        exp_neighbors = self.grid.get_neighborhood(target, moore=False, include_center=False)
        
        for exp_neighbor in exp_neighbors:
            if self.direction(target, exp_neighbor) == direction and \
               exp_neighbor != origin:
                if self.check_collision_walls_doors(target, exp_neighbor):
                    self.register_damage_walls_doors(target, exp_neighbor)
                    break
                elif self.grid_details.get(exp_neighbor) == 0 or \
                   self.grid_details.get(exp_neighbor) == 1:
                    self.grid_details[exp_neighbor] = 2
                    self.boo_zones.append(exp_neighbor)
                    print(f"[INFO] Nuevo fuego extendido de {target} a {exp_neighbor}")
                    if self.grid_details.get(exp_neighbor) == 0:
                        self.log_event({
                            "type": "fire_extended",
                            "from": target,
                            "to": exp_neighbor,
                            "step": self.step_count
                        })
                    if self.grid_details.get(exp_neighbor) == 1:
                        self.log_event({
                        "type": "fire_to_smoke",
                        "position": exp_neighbor,
                        "step": self.step_count
                    })
                    break
                elif self.grid_details.get(exp_neighbor) == 2:
                    self.trigger_explosion(target,exp_neighbor)
                    break
                else:
                    pass
        
        return


    def trigger_wave(self, position):
        """Desencadena una oleada de incendios."""
        pass
    
    def direction(self, start, next):
        """Calcula la dirección de movimiento entre dos posiciones."""
        delta_x = next[0] - start[0]
        delta_y = next[1] - start[1]
        # Si no hay cambio en X (movimiento vertical)
        if delta_x == 0:
            if delta_y < 0:
                return 0  # Movimiento hacia arriba (Norte)
            else:
                return 2  # Movimiento hacia abajo (Sur)

        # Si no hay cambio en Y (movimiento horizontal)
        elif delta_y == 0:
            if delta_x < 0:
                return 1  # Movimiento hacia la izquierda (Oeste)
            else:
                return 3  # Movimiento hacia la derecha (Este)

    def check_collision_walls_doors(self, start, next):
        """Verifica si hay una colisión entre dos posiciones."""
        direction = self.direction(start, next)
        wall_blocked = direction != None and self.grid_walls[start][0][direction] == '1'
        if start in self.exit_positions and next in self.exit_positions:
            doors_blocked = not (self.exit_positions[start] and self.exit_positions[next])
        else:
            doors_blocked = True
        return wall_blocked and doors_blocked

    def process_flashover(self):
        """Procesa la expansión de incendios y fantasmas."""
        smoke_cells = [pos for pos, val in self.grid_details.items() if val == 1]
        for smoke_cell in smoke_cells:
            neighbors = self.grid.get_neighborhood(smoke_cell, moore=False, include_center=False)
            for neighbor in neighbors:
                if self.grid_details[neighbor] == 2:
                    self.grid_details[smoke_cell] = 2
                    break
        for point in list(self.portraits):
            if self.grid_details[point] == 2:
                del self.portraits[point]
                self.casualties += 1
                break
    
    #def process_flashover(self):
    #    """Procesa la expansión de incendios y verifica condiciones de explosión."""
    #    smoke_cells = [pos for pos, val in self.grid_details.items() if val == 1]
    #    for smoke_cell in smoke_cells:
    #        neighbors = self.grid.get_neighborhood(smoke_cell, moore=False, include_center=False)
    #        for neighbor in neighbors:
    #            if self.grid_details[neighbor] == 2:  # Fuego cerca del humo
    #                #self.trigger_explosion(smoke_cell)  # Inicia explosión
    #                break

    def update_simulation_status(self):
        """Actualiza el estado de la simulación."""
        if self.casualties >= 4 or self.damage_counter >= 24:
            self.simulation_status = "Defeat"
            return True
        elif self.rescued >= 7:
            self.simulation_status = "Victory"
            return True
        return False
    
    def print_schedule(self):
        print("Agentes en el Scheduler:")
        for agent in self.schedule.agents:
            print(f"Agente {agent.unique_id} con rol {agent.role} en posición {agent.pos}")

    def step(self):
        """Evoluciona un paso del modelo."""
        print(f"\n--- Turno {self.step_count} ---")
        self.datacollector.collect(self)  # Recolectar datos para análisis

        # Verificar si la simulación debe detenerse
        if self.update_simulation_status():
            print(f"[DEBUG] Estatus de la simulación: {self.simulation_status}")
            return

        self.step_count += 1
        print("[DEBUG] Iniciando pasos de los agentes en orden:")

        # Iterar sobre los agentes según su ID
        for agent in sorted(self.schedule.agents, key=lambda a: a.unique_id):
            agent.step()

        # Mostrar la energía restante de todos los agentes al final del turno
        print("\n[DEBUG] Energía de los agentes al final del turno:")
        for agent in sorted(self.schedule.agents, key=lambda a: a.unique_id):
            print(f"  - Agente {agent.unique_id} ({agent.role}): {agent.action_points} de energía.")
        
        # Realizar procesos adicionales del modelo
        self.process_flashover()
        self.add_portraits()
        self.update_simulation_status()