# Importación de módulos necesarios
import heapq            # Biblioteca para trabajar con colas de prioridad
from mesa import Agent  # Clase base para agentes en simulaciones con Mesa
from queue import Queue # Cola FIFO
import random           # Biblioteca para generar valores aleatorios

DEVELOPMENT = False  # Bandera de desarrollo

# Clase que representa un agente "Luigi" en la simulación
class LuigiAgent(Agent):
    # Constructor de la clase LuigiAgent
    # Inicializa al agente con un rol, posición inicial y otros atributos para su estado y acciones
    def __init__(self, unique_id, model, role, position):
        super().__init__(unique_id, model)  # Llama al constructor de la clase base `Agent`
        self.role = role                    # Rol asignado al agente, que puede influir en su comportamiento
        self.pos = None                     # Posición actual del agente en la cuadrícula, inicialmente `None`
        self.model = model                  # Referencia al modelo al que pertenece el agente
        self.history = []                   # Historial de posiciones del agente
        self.action_history = []            # Historial de acciones realizadas por el agente
        self.action_points = 4              # Puntos de acción disponibles por turno
        self.carrying_portrait = False      # Indica si el agente está llevando un retrato
        self.in_central_grid = False        # Indica si el agente está en la cuadrícula central
        self.start_position = position      # Posición inicial del agente


    # Función para reiniciar el estado del agente
    # Resetea los atributos del agente y lo mueve a su posición inicial si es necesario
    def reset(self):
        # Resetea el estado de carga de retratos
        self.carrying_portrait = False
        # Resetea el estado de estar en la cuadrícula central
        self.in_central_grid = False

        # Mensaje de depuración indicando que el agente ha sido reiniciado
        print(f"[DEBUG] Agente {self.unique_id} ha muerto.")

        # Si el agente tiene una posición inicial definida, lo mueve a esa posición
        if self.start_position:
            self.model.grid.move_agent(self, self.start_position)
            self.pos = self.start_position

            # Mensaje de depuración indicando el movimiento a la posición inicial
            print(f"[DEBUG] Agente {self.unique_id} movido a su posición inicial {self.start_position}.")
        
        # Registra el evento de movimiento en el modelo
        self.model.log_event({
            "type": "agent_move",           # Tipo de evento: movimiento del agente
            "agent": self.unique_id,        # ID único del agente
            "from": self.start_position,    # Posición inicial del movimiento
            "to": self.start_position,      # Posición final del movimiento
        })

    # Calcula una heurística basada en la distancia de Manhattan más un factor aleatorio
    def manhattan_heuristic(self, cell, goal):
        # Calcula la heurística Manhattan entre dos celdas
        # La distancia de Manhattan es la suma de las diferencias absolutas 
        # entre las coordenadas de las dos celdas
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]) + random.uniform(0, 0.5)
        # Se agrega un factor aleatorio para romper posibles empates

    # Implementa el algoritmo de Dijkstra para encontrar el camino más corto entre puntos
    def dijkstra(self, details, ptk, goals):
        # Inicializa un diccionario para almacenar 
        # los costos acumulados desde el punto inicial
        path_cost = {ptk: 0}
        
        # Inicializa un conjunto para rastrear los nodos 
        # ya visitados
        path_close = set()
        # Inicializa un diccionario para mapear cada nodo a 
        # su nodo anterior en el camino
        path_past = {}
        # Inicializa la cola de prioridad

        # Inicializa una cola de prioridad para manejar los nodos abiertos,
        # comenzando con el nodo inicial `ptk` y un costo de 0
        analize_path = [(0, ptk)]
        # Si hay objetivos definidos (lista de metas no vacía)
        if len(goals) >= 1:
            
            # Mientras haya nodos por evaluar en la cola de prioridad
            while analize_path:
                # Extrae el nodo con menor costo acumulado 
                # de la cola de prioridad
                _, present_node = heapq.heappop(analize_path)
                
                # Si el nodo actual es uno de los objetivos,
                # construye el camino más corto
                if present_node in goals:
                    # Construye el camino mas corto
                    path = []
                    
                    # Retrocede desde el nodo actual hasta el 
                    # nodo inicial utilizando `path_past`
                    while present_node in path_past:
                        path.append(present_node)

                        present_node = path_past[present_node]
                    # Devuelve el camino invertido
                    return path[::-1]

                # Marca el nodo actual como visitado añadiéndolo al conjunto `path_close`
                path_close.add(present_node)
                
                # Explora todos los vecinos (adyacentes) del nodo actual
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    # Calcula las coordenadas del vecino
                    x, y = present_node[0] + dx, present_node[1] + dy
                    neighbor = (x, y)

                    # Si el vecino no es válido (fuera de los 
                    # detalles del modelo), lo omite
                    if neighbor not in details:
                        continue

                    # Si el vecino ya ha sido visitado, lo omite
                    if neighbor in path_close:
                        continue

                    # Obtiene el costo base del vecino desde `details`
                    cost = details[neighbor]

                    # Penaliza obstáculos para que no tome ese path tan seguido
                    # Cada path tiene un costo fijo
                    # Esto para que pueda escoger el camino mas corto

                    # Penaliza paredes para que no tome ese path tan seguido
                    if self.check_collision_walls(present_node, neighbor):
                        cost += 4
                    
                    # Penaliza puertas para que prefiera el path sin ningun obstaculo
                    if self.check_collision_doors(present_node, neighbor):
                        cost += 1

                    # Calcula el costo tentativo para llegar al vecino
                    for_the_moment_cost = path_cost[present_node] + cost
                    
                    # Si el vecino no tiene costo registrado o el costo tentativo es menor,
                    # lo actualiza
                    if neighbor not in path_cost or for_the_moment_cost < path_cost[neighbor]:
                        # Actualiza el costo del vecino
                        path_cost[neighbor] = for_the_moment_cost
                        # Calcula las heurísticas hacia todos los objetivos desde el vecino
                        valid_goals = [self.manhattan_heuristic(neighbor, goal) for goal in goals]
                        

                        # Determina la prioridad del vecino considerando el costo y la heurística
                        if valid_goals:
                            priority = for_the_moment_cost + min(valid_goals)
                        else:
                            # Si no hay heurísticas válidas, usa una heurística hacia el punto inicial
                            priority = for_the_moment_cost + self.manhattan_heuristic(neighbor, ptk)

                        # Añade el vecino a la cola de prioridad
                        heapq.heappush(analize_path, (priority, neighbor))
                        # Registra de dónde vino el vecino
                        path_past[neighbor] = present_node
            
            # Si no hay camino, devuelve posición inicial
            return [ptk]
        
        else:
            # Sin objetivos, retorna posición inicial
            return [ptk]
    
    # Verifica si existe una pared entre dos puntos
    def check_collision_walls(self, start, next):
        direction = self.model.direction(start, next)
        combined_possn = start + next
        combined_posns = next + start

        if start in self.model.grid_walls:
            wall_blocked = direction is not None and self.model.grid_walls[start][0][direction] == '1'
        else:
            wall_blocked = False

        if (combined_possn in self.model.exit_positions or 
            combined_posns in self.model.exit_positions):
            wall_blocked = False
        
        return wall_blocked

    # Verifica si hay una puerta cerrada entre dos posiciones
    def check_collision_doors(self, start, next):
        combined_possn = start + next
        combined_posns = next + start

        if combined_possn in self.model.exit_positions or \
           combined_posns in self.model.exit_positions:
            if self.model.exit_positions.get(combined_possn) and \
               self.model.exit_positions.get(combined_posns):
                doors_blocked = False
            else:
                doors_blocked = True
        else:
            doors_blocked = False
        return doors_blocked

    # Mueve al agente hacia un objetivo utilizando el algoritmo Dijkstra
    def move_towards(self, target):
        # Mueve al agente hacia un objetivo usando Dijkstra
        if self.pos == target:
            return True

        path = self.dijkstra(self.model.grid_details, self.pos, [target])
        print(f"[DEBUG] Agente {self.unique_id} tiene el camino: {path}")
        if not path:
            print(f"[DEBUG] Agente {self.unique_id} no puede alcanzar el objetivo desde {self.pos}.")
            return False

        next_step = path[0]
        print(f"[DEBUG] Agente {self.unique_id} se mueve de {self.pos} a {next_step}.")
        self.model.log_event({
            "type": "agent_move",
            "agent": self.unique_id,
            "from": self.pos,
            "to": next_step,
        })
        self.model.grid.move_agent(self, next_step)
        self.pos = next_step
        self.history.append(self.pos)

        self.action_points -= 2 if self.carrying_portrait else 1
        return True

    # Examina un retrato en una posición y determina si es una víctima o una falsa alarma
    def examine_portrait(self, position):
        if position in self.model.portraits:
            portrait = self.model.portraits[position]
            if portrait == "victim":
                self.carrying_portrait = True
                self.model.portraits[position] = None
                print(f"Agente {self.unique_id} ha encontrado una víctima en {position}.")
                self.action_history.append(f"Portrait found at: {position}, Type: Victim")
                self.model.log_event({
                    "type": "found_portrait",
                    "at": position,
                    "agent": self.unique_id,
                    "portrait_type": "victim",
                })
                return {"position": position, "type": "victim"}
            elif portrait == "false_alarm":
                self.model.portraits[position] = None
                print(f"Agente {self.unique_id} encontró una falsa alarma en {position}.")
                self.action_history.append(f"Portrait found at: {position}, Type: False")
                self.model.log_event({
                    "type": "found_portrait",
                    "at": position,
                    "agent": self.unique_id,
                    "portrait_type": "False",
                })
                return {"position": position, "type": "false_alarm"}
        return None

    # Apaga un fuego en una posición específica si tiene suficientes puntos de acción
    def extinguish_fire(self, position):
        if self.action_points >= 2:
            print(f"[DEBUG] Agente: {self.unique_id} fuego apagado en {position}.")
            self.model.grid_details[position] = 0
            self.action_points -= 2
            self.action_history.append(f"Fire extinguished at: {position}") 
            self.model.log_event({
                    "type": "fire_extinguished",
                    "agent": self.unique_id,
                    "at": position,
                })
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {position}.")

    def extinguish_smoke(self, position, reducing):
        if self.action_points >= 1:
            print(f"[DEBUG] Agente {self.unique_id} eliminó el humo en {position}.")
            self.model.grid_details[position] -= 1
            self.action_points -= 1
            if reducing == False:
                self.action_history.append(f"Smoke extinguished at: {position}") 
                self.model.log_event({
                        "type": "fire_to_smoke",
                        "agent": self.unique_id,
                        "at": position,
                    })
            else:
                print(f"[DEBUG] Agente {self.unique_id} reduce el fuego a humo en {position}.")
                self.model.log_event({
                    "type": "smoke_extinguished",
                    "agent": self.unique_id,
                    "position": position,
                })
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar humo en {position}.")

    def move_inside_central_grid(self):
        if (self.pos[0] == 0):
            next_step = (1, self.pos[1])
        elif (self.pos[1] == 0):
            next_step = (self.pos[0], 1)
        elif (self.pos[0] == self.model.grid.width - 1):
            next_step = (self.model.grid.width - 2, self.pos[1])
        elif (self.pos[1] == self.model.grid.height - 1):
            next_step = (self.pos[0], self.model.grid.height - 2)
        
        if self.model.grid_details[next_step] == 2:
            self.extinguish_fire(next_step)
        
        self.in_central_grid = True
        self.action_points -= 1
        self.model.grid.move_agent(self, next_step)
        self.pos = next_step
        self.history.append(self.pos)

        print(f"[DEBUG] Agente {self.unique_id} se mueve dentro del cuadrante central en {self.pos}.")
        self.model.log_event({
            "type": "agent_move",
            "from": self.pos,
            "agent": self.unique_id,
            "to": next_step,
        })

    def rescuer_strategy(self):
        while self.action_points > 0:
            if DEVELOPMENT:
                self.action_points -= 1
                continue

            if self.handle_fire_around():
                continue

            if self.carrying_portrait:
                valid_exits = [pos for pos in self.model.entrances if isinstance(pos, tuple) and len(pos) == 2]
                if valid_exits:
                    nearest_exit = min(valid_exits, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} lleva retrato. Moviéndose hacia la salida más cercana: {nearest_exit}")

                    if self.handle_fire_around():
                        continue
                    
                    if self.check_collision_walls(self.pos, nearest_exit):
                        if self.action_points >= 2:
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_exit}. Rompiendo pared.")
                            self.break_wall(self.pos, nearest_exit)
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                            break
                    elif self.check_collision_doors(self.pos, nearest_exit):
                        if self.action_points >= 1:
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una puerta cerrada entre {self.pos} y {nearest_exit}. Abriendo puerta.")
                            self.open_door(self.pos, nearest_exit)
                            print("Logeando abrir puerta")
                            self.model.log_event({
                                "type": "open_door",
                                "agent": self.unique_id,
                                "position": self.pos,
                                "target": nearest_exit,
                            })
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                            break
                    
                    if self.pos == nearest_exit:
                        print(f"[DEBUG] Agente {self.unique_id} ha llegado a la salida con el retrato.")
                        self.carrying_portrait = False
                        self.model.rescued += 1
                        print(f"[DEBUG] Agente {self.unique_id} ha rescatado a una víctima. Total rescatados: {self.model.rescued}")
                        self.model.log_event({
                            "type": "rescued_portrait",
                            "agent": self.unique_id,
                            "position": nearest_exit,
                            "rescued": self.model.rescued,
                        })

                    if self.action_points >= 2:
                        self.move_towards(nearest_exit)
                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para moverse hacia {nearest_exit}.")
                    
                    if self.action_points < 2:
                        break
                else:
                    print(f"[ERROR] No hay salidas válidas para el agente {self.unique_id}. Terminando turno.")
                    break 
            else:
                if not self.in_central_grid:
                    self.move_inside_central_grid()
                else:
                    portraits = [
                        pos for pos, label in self.model.portraits.items()
                        if label in ["victim", "false_alarm"] and isinstance(pos, tuple) and len(pos) == 2
                    ]
                    if portraits:
                        nearest_portrait = min(portraits, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                        print(f"[DEBUG] Agente {self.unique_id} buscando retrato. Moviéndose hacia el retrato más cercano: {nearest_portrait}")

                        if self.handle_fire_around():
                            continue
                        
                        if self.check_collision_walls(self.pos, nearest_portrait):
                            if self.action_points >= 2:
                                print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_portrait}. Rompiendo pared.")
                                self.break_wall(self.pos, nearest_portrait)
                            else:
                                print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                                break
                        elif self.check_collision_doors(self.pos, nearest_portrait):
                            if self.action_points >= 1:
                                print(f"[DEBUG] Agente {self.unique_id} encuentra una puerta cerrada entre {self.pos} y {nearest_portrait}. Abriendo puerta.")
                                self.open_door(self.pos, nearest_portrait)
                                print("Logeando abrir puerta")
                                self.model.log_event({
                                    "type": "open_door",
                                    "agent": self.unique_id,
                                    "position": self.pos,
                                    "target": nearest_portrait,
                                })
                            else:
                                print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                                break

                        if not self.move_towards(nearest_portrait):
                            break

                        if self.pos == nearest_portrait:
                            if not self.examine_portrait(nearest_portrait):
                                continue
                    else:
                        print(f"[DEBUG] No hay más retratos para el agente {self.unique_id}. Terminando turno.")
                        break

    def firefighter_strategy(self):
        visited_positions = set()
        while self.action_points > 0:
            if DEVELOPMENT:
                self.action_points -= 1
                continue

            if not self.in_central_grid:
                self.move_inside_central_grid()
            else:
                fire_cells = [pos for pos, value in self.model.grid_details.items() if value == 1 or value == 2]
                if fire_cells:
                    nearest_fire = min(fire_cells, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} buscando fuego. Moviéndose hacia el fuego más cercano: {nearest_fire}")

                    if nearest_fire not in visited_positions:
                        visited_positions.add(nearest_fire)

                    if self.handle_fire_around():
                        continue

                    if self.check_collision_walls(self.pos, nearest_fire):
                        if self.action_points >= 2:
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_fire}. Rompiendo pared.")
                            self.break_wall(self.pos, nearest_fire)
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                            break
                    elif self.check_collision_doors(self.pos, nearest_fire):
                        if self.action_points >= 1:
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una puerta cerrada entre {self.pos} y {nearest_fire}. Abriendo puerta.")
                            self.open_door(self.pos, nearest_fire)
                            self.model.log_event({
                                "type": "open_door",
                                "agent": self.unique_id,
                                "position": self.pos,
                                "target": nearest_fire,
                            })
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                            break

                    fire_value = self.model.grid_details[nearest_fire]
                    if fire_value == 2 and self.action_points < 2:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para extinguir fuego.")
                        break
                    elif fire_value == 1 and self.action_points < 1:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para extinguir humo.")
                        break
                    
                    if not self.move_towards(nearest_fire):
                        break

                    if self.pos == nearest_fire:
                        if fire_value == 2:
                            if self.action_points >= 2:
                                self.extinguish_fire(nearest_fire)
                            elif self.action_points == 1:
                                reducing = True
                                self.extinguish_smoke(nearest_fire, reducing)
                                print(f"[DEBUG] Agente {self.unique_id} bajando fuego a humo . El fuego es : {nearest_fire}")
                                self.action_history.append(f"Fire reduced to smoke at: {nearest_fire}")
                        elif fire_value == 1:
                            reducing = False
                            self.extinguish_smoke(nearest_fire, reducing)
                        continue
                else:
                    print(f"[DEBUG] Agente {self.unique_id} no encuentra más fuego ni humo.")
                    break
    
    def handle_fire_around(self):
        """Verifica si hay fuego o humo en las celdas vecinas y los apaga si es posible."""
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        for neighbor in neighbors:
            if neighbor in self.model.grid_details:
                if self.model.grid_details[neighbor] == 2:
                    if self.action_points >= 2:
                        if not self.check_collision_walls(self.pos, neighbor):
                            self.extinguish_fire(neighbor)
                            return True
                        else:
                            self.break_wall(self.pos, neighbor)
                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {neighbor}. Puntos disponibles: {self.action_points}")
                elif self.model.grid_details[neighbor] == 1:
                    if self.action_points >= 1:
                        if not self.check_collision_walls(self.pos, neighbor):
                            reducing = True
                            self.extinguish_smoke(neighbor,reducing)
                            return True
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no puede romper paredes para apagar humo en {neighbor}.")
                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar humo en {neighbor}. Puntos disponibles: {self.action_points}")
        return False

        # Actualiza las paredes en la cuadrícula después de romper una pared
        # `origin` y `target` son las celdas adyacentes donde se rompe la pared
        # `direction_sn` y `direction_ns` son las direcciones relativas entre las celdas
    def update_grid_walls(self, origin, target, direction_sn, direction_ns):
        # Obtiene las paredes de la celda de origen como lista
        origin_wall = list(self.model.grid_walls[origin][0])

        # Obtiene las paredes de la celda de destino como lista
        target_wall = list(self.model.grid_walls[target][0])
        # Marca como rota la pared en la dirección `direction_sn` desde el origen
        origin_wall[direction_sn]= "0"

        # Marca como rota la pared en la dirección `direction_ns` desde el destino
        target_wall[direction_ns]= "0"

        # Convierte las listas de paredes actualizadas de nuevo a cadenas y actualiza el modelo
        self.model.grid_walls[origin][0] = ''.join(origin_wall)
        self.model.grid_walls[target][0] = ''.join(target_wall)

    # Rompe una pared entre dos celdas adyacentes.
    # `start` es la celda inicial y `next` la celda objetivo.
    def break_wall(self, start, next):
        # Determina la dirección de `start` a `next`
        direction_sn = self.model.direction(start, next)
        # Determina la dirección opuesta, de `next` a `start`
        direction_ns = self.model.direction(next, start)

        # Si hay una dirección válida
        if direction_sn is not None:
             # Actualiza las paredes en la cuadrícula
            self.update_grid_walls(start, next, direction_sn, direction_ns)
            # Registra la acción en el historial
            self.action_history.append(f"break wall:{start}-{next}")
            # Resta 2 puntos de acción por romper una pared
            self.action_points -= 2
            # Incrementa el contador de daños en el modelo
            self.model.damage_counter +=1
            
            print(f"[DEBUG] Agente {self.unique_id} rompió la pared {next}.")
            
            # Registra el evento en el modelo
            self.model.log_event({
                "type": "wall_destroyed", # Define el tipo de evento como "wall_destroyed"
                "agent": self.unique_id,  # Identifica al agente que realizó la acción mediante su ID único
                "position": start,        # Registra la posición inicial desde donde se rompió la pared
                "target": next            # Registra la posición objetivo donde estaba la pared rota
            })

    # Abre una puerta entre dos celdas
    # `coord1` y `coord2` son las celdas adyacentes donde se encuentra la puerta
    def open_door(self,coord1, coord2):
        if coord1 in self.model.exit_positions and coord2 in self.model.exit_positions:
            # Marca la puerta como abierta en ambas posiciones
            self.model.exit_positions[coord1] = True
            self.model.exit_positions[coord2] = True

            # Registra la acción en el historial
            self.action_history.append(f"open door:{coord1}-{coord2}")
            # Resta 1 punto de acción por abrir la puerta
            self.action_points -= 1


    # Cierra una puerta entre dos celdas
    # `coord1` y `coord2` son las celdas adyacentes donde se encuentra la puerta
    def close_door(self,coord1, coord2):
        
        if coord1 in self.model.exit_positions and coord2 in self.model.exit_positions:
            # Marca la puerta como cerrada en ambas posiciones
            self.model.exit_positions[coord1] = False
            self.model.exit_positions[coord2] = False
            # Registra la acción en el historial
            self.action_history.append(f"close door:{coord1}-{coord2}")
            # Resta 1 punto de acción por cerrar la puerta
            self.action_points -= 1


    # Define las acciones que realiza el agente en un turno
    def step(self):
        print(f"\n[DEBUG] Agente {self.unique_id} ({self.role}) inicia su turno en posición {self.pos}. Energía inicial: {self.action_points}.")

        if self.role == "rescuer":        # Si el rol del agente es rescatista
            self.rescuer_strategy()       # Ejecuta la estrategia de rescatista
        elif self.role == "firefighter":  # Si el rol del agente es bombero
            self.firefighter_strategy()   # Ejecuta la estrategia de bombero

        print(f"[DEBUG] Agente {self.unique_id} ({self.role}) termina su turno en posición {self.pos}. Energía restante: {self.action_points}.")

        # Añade retratos al modelo (si corresponde)
        self.model.add_portraits()
        # Extiende obstáculos o enemigos en el modelo (si corresponde)
        self.model.spread_boos()

        # Recarga puntos de acción para el siguiente turno
        self.action_points += 4


    # Alterna el estado de `carrying_portrait`.
    # Si el agente lleva un retrato, deja de llevarlo, y viceversa.
    def toggle_point(self):
        # Cambia el estado del retrato
        self.carrying_portrait = not self.carrying_portrait
        print(f"Agente {self.unique_id} ahora {'lleva un retrato' if self.carrying_portrait else 'no lleva un retrato'}.")