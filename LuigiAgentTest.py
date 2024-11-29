import heapq
from mesa import Agent
from queue import Queue

import random

DEVELOPMENT = False

class LuigiAgent(Agent):
    """Agente que simula a Luigi en el modelo de rescate y bombero."""

    def __init__(self, unique_id, model, role):
        super().__init__(unique_id, model)
        self.role              = role  # rol: 'rescuer' o 'firefighter'
        self.pos               = None  # Posición del agente en el grid
        self.model             = model
        self.history           = []  # Histórico de movimientos
        self.action_history    = []  # Histórico de acciones
        self.action_points     = 4  # Puntos de acción para cada turno
        self.carrying_portrait = False  # Indica si el agente lleva un retrato (víctima)
        self.in_central_grid   = False  # Indica si el agente se encuentra dentro del grid central

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
                        cost += 2
                    
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
    
    
    def check_collision_walls(self, start, next):
        """Verifica si hay una colisión entre dos posiciones."""
        direction = self.model.direction(start, next)
        combined_possn = start + next
        combined_posns = next + start

        # Verifica si la posición 'start' está en el grid_walls
        if start in self.model.grid_walls:
            wall_blocked = direction is not None and self.model.grid_walls[start][0][direction] == '1'
        else:
            wall_blocked = False  # No hay colisión si la posición no está en el grid

        # Comprueba si la posición combinada está en las salidas
        if (combined_possn in self.model.exit_positions or 
            combined_posns in self.model.exit_positions):
            wall_blocked = False  # No bloquear si está en una posición de salida
        
        return wall_blocked


    def check_collision_doors(self, start, next):
        """Verifica si hay una colisión entre dos posiciones."""
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

    def move_towards(self, target):
        """Mueve al agente hacia un objetivo usando A*."""
        if self.pos == target:
            return True  # El agente ya está en la celda objetivo

        path = self.dijkstra(self.model.grid_details, self.pos, [target])
        print(f"Agente {self.unique_id} tiene el camino: {path}")
        if not path:
            print(f"Agente {self.unique_id} no puede alcanzar el objetivo desde {self.pos}.")
            return False  # No se encontró un camino

        next_step = path[0]
        print(f"Agente {self.unique_id} se mueve de {self.pos} a {next_step}.")
        self.model.log_event({
            "type": "agent_move",
            "agent": self.unique_id,
            "from": self.pos,
            "to": next_step,
        })
        self.model.grid.move_agent(self, next_step)
        self.pos = next_step
        self.history.append(self.pos)

        # Reducir puntos de acción según si lleva un retrato
        self.action_points -= 2 if self.carrying_portrait else 1
        return True

    def examine_portrait(self, position):
        """Recoge el retrato de la víctima o falsa alarma cuando el agente llega a su posición."""
        if position in self.model.portraits:
            portrait = self.model.portraits[position]
            if portrait == "victim":
                self.carrying_portrait = True  # El agente ahora lleva un retrato (víctima)
                self.model.portraits[position] = None  # Eliminar la víctima rescatada
                print(f"Agente {self.unique_id} ha encontrado una víctima en {position}.")
                self.action_history.append(f"Portrait found at: {position}, Type: Victim")
                self.model.log_event({
                    "type": "found_portrait",
                    "at": position,
                    "agent": self.unique_id,
                    "portrait_type": "victim",
                })
                return {"position": position, "type": "victim"}  # Retorna detalles
            elif portrait == "false_alarm":
                self.model.portraits[position] = None  # Eliminar la falsa alarma
                print(f"Agente {self.unique_id} encontró una falsa alarma en {position}.")
                self.action_history.append(f"Portrait found at: {position}, Type: False")
                self.model.log_event({
                    "type": "found_portrait",
                    "at": position,
                    "agent": self.unique_id,
                    "portrait_type": "False",
                })
                return {"position": position, "type": "false_alarm"}  # Retorna detalles
        return None  # Si no hay retrato en esa posición

    def extinguish_fire(self, position):
        """Extinguir fuego en la posición dada."""
        if self.action_points >= 2:
            print(f"[DEBUG] Agente {self.unique_id} apagando fuego en {position}.")
            self.model.grid_details[position] = 0  # Actualizar la celda a estado vacío
            self.action_points -= 2  # Reducir puntos de acción
            self.action_history.append(f"Fire extinguished at: {position}") 
            self.model.log_event({
                    "type": "fire_extinguished",
                    "agent": self.unique_id,
                    "at": position,
                })
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {position}.")

    def extinguish_smoke(self, position, reducing):
        """Extinguir humo en la posición dada."""
        if self.action_points >= 1:
            print(f"[DEBUG] Agente {self.unique_id} eliminando humo en {position}.")
            self.model.grid_details[position] -= 1   # Actualizar la celda a estado vacío
            self.action_points -= 1  # Reducir puntos de acción
            if not reducing:
                self.action_history.append(f"Smoke extinguished at: {position}") 
                self.model.log_event({
                        "type": "smoke_extinguished",
                        "agent": self.unique_id,
                        "at": position,
                    })
            else:
                print(f"[DEBUG] Agente {self.unique_id} reduce el fuego a humo en {position}.")
                self.model.log_event({
                    "type": "fire_to_smoke",
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
        """Estrategia para agentes cuyo rol es rescatar víctimas."""
        while self.action_points > 0:
            if DEVELOPMENT:
                self.action_points -= 1
                continue

            if self.carrying_portrait:
                # Si lleva un retrato, moverse hacia la salida más cercana
                valid_exits = [pos for pos in self.model.entrances if isinstance(pos, tuple) and len(pos) == 2]
                if valid_exits:
                    nearest_exit = min(valid_exits, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} lleva retrato. Moviéndose hacia la salida más cercana: {nearest_exit}")
                    
                    # Verificar si hay puertas o paredes en el camino
                    if self.check_collision_walls(self.pos, nearest_exit):
                        if self.action_points >= 2:  # Verificar si tiene puntos para romper la pared
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_exit}. Rompiendo pared.")
                            self.break_wall(self.pos, nearest_exit)
                            self.model.log_event({
                                "type": "wall_destroyed",
                                "agent": self.unique_id,
                                "position": self.pos,
                                "target": nearest_exit,
                            })
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                            break
                    elif self.check_collision_doors(self.pos, nearest_exit):
                        if self.action_points >= 1:  # Verificar si tiene puntos para abrir la puerta
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una puerta cerrada entre {self.pos} y {nearest_exit}. Abriendo puerta.")
                            self.open_door(self.pos, nearest_exit)
                            self.model.log_event({
                                "type": "open_door",
                                "agent": self.unique_id,
                                "position": self.pos,
                                "target": nearest_exit,
                            })
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                            break
                    
                    # Si el agente llega a la salida, se rescató la víctima
                    if self.pos == nearest_exit:
                        print(f"[DEBUG] Agente {self.unique_id} ha llegado a la salida con el retrato.")
                        self.carrying_portrait = False  # Resetear estatus de
                        self.model.rescued += 1  # Contar el rescate en el modelo
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
                    # Buscar el retrato más cercano (víctima o falsa alarma)
                    portraits = [
                        pos for pos, label in self.model.portraits.items()
                        if label in ["victim", "false_alarm"] and isinstance(pos, tuple) and len(pos) == 2
                    ]
                    if portraits:
                        # Encontrar el retrato más cercano usando Manhattan
                        nearest_portrait = min(portraits, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                        print(f"[DEBUG] Agente {self.unique_id} buscando retrato. Moviéndose hacia el retrato más cercano: {nearest_portrait}")
                        
                        # Verificar si hay puertas o paredes en el camino
                        if self.check_collision_walls(self.pos, nearest_portrait):
                            if self.action_points >= 2:  # Verificar si tiene puntos para romper la pared
                                print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_portrait}. Rompiendo pared.")
                                self.break_wall(self.pos, nearest_portrait)
                                self.model.log_event({
                                    "type": "wall_destroyed",
                                    "agent": self.unique_id,
                                    "position": self.pos,
                                    "target": nearest_portrait,
                                })
                            else:
                                print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                                break
                        elif self.check_collision_doors(self.pos, nearest_portrait):
                            if self.action_points >= 1:  # Verificar si tiene puntos para abrir la puerta
                                print(f"[DEBUG] Agente {self.unique_id} encuentra una puerta cerrada entre {self.pos} y {nearest_portrait}. Abriendo puerta.")
                                self.open_door(self.pos, nearest_portrait)
                                self.model.log_event({
                                    "type": "open_door",
                                    "agent": self.unique_id,
                                    "position": self.pos,
                                    "target": nearest_portrait,
                                })
                            else:
                                print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                                break

                        if not self.move_towards(nearest_portrait):  # Si no puede moverse, detenerse
                            break
                        
                        # Verificar si llegó al retrato y procesarlo
                        if self.pos == nearest_portrait:
                            if not self.examine_portrait(nearest_portrait):  # Si no es una víctima, sigue buscando otro retrato
                                continue
                    else:
                        print(f"[DEBUG] No hay más retratos para el agente {self.unique_id}. Terminando turno.")
                        break

    def manhattan_heuristic(self, cell, goal):
        # Calcula la heurística Manhattan entre dos celdas

        # La distancia de Manhattan es la suma de las diferencias absolutas 
        # entre las coordenadas de las dos celdas
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]) + random.uniform(0, 0.5)
        # Se agrega un factor aleatorio para romper posibles empates

    def firefighter_strategy(self):
        """Estrategia para agentes cuyo rol es apagar incendios."""
        while self.action_points > 0:
            if DEVELOPMENT:
                self.action_points -= 1
                continue

            if not self.in_central_grid:
                self.move_inside_central_grid()
            else:
                # Buscar la celda más cercana con humo (valor 1) o fuego (valor 2)
                fire_cells = [pos for pos, value in self.model.grid_details.items() if value == 1 or value == 2]
                if fire_cells:
                    nearest_fire = min(fire_cells, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} buscando fuego. Moviéndose hacia el fuego más cercano: {nearest_fire}")

                    # Verificar si hay puertas o paredes en el camino
                    if self.check_collision_walls(self.pos, nearest_fire):
                        if self.action_points >= 2:  # Verificar si tiene puntos para romper la pared
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_fire}. Rompiendo pared.")
                            self.break_wall(self.pos, nearest_fire)
                            self.model.log_event({
                                "type": "wall_destroyed",
                                "agent": self.unique_id,
                                "position": self.pos,
                                "target": nearest_fire,
                            })
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                            break
                    elif self.check_collision_doors(self.pos, nearest_fire):
                        if self.action_points >= 1:  # Verificar si tiene puntos para abrir la puerta
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

                    # Verificar si hay puntos de acción antes de moverse
                    fire_value = self.model.grid_details[nearest_fire]
                    if fire_value == 2 and self.action_points < 2:  # Fuego requiere al menos 2 puntos
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para extinguir fuego.")
                        break
                    elif fire_value == 1 and self.action_points < 1:  # Humo requiere al menos 1 punto
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para extinguir humo.")
                        break

                    # Si tiene suficientes puntos, intentar moverse
                    if not self.move_towards(nearest_fire):  # Si no puede moverse hacia el fuego, detenerse
                        break

                    # Verificar si llegó al humo/fuego y procesarlo
                    if self.pos == nearest_fire:
                        if fire_value == 2:  # Si es fuego
                            # Dependiendo de puntos, extinguir o reducir a humo
                            if self.action_points >= 2:
                                self.extinguish_fire(nearest_fire)
                            elif self.action_points == 1:
                                reducing = True
                                self.extinguish_smoke(nearest_fire, reducing)
                                print(f"[DEBUG] Agente {self.unique_id} bajando fuego a humo . El fuego es : {nearest_fire}")
                                self.action_history.append(f"Fire reduced to smoke at: {nearest_fire}")
                        elif fire_value == 1:  # Si es humo
                            reducing = False
                            self.extinguish_smoke(nearest_fire, reducing)
                        continue  # Después de lidiar con el humo/fuego, sigue buscando otro
                else:
                    # Si no hay fuego, el bombero se detiene
                    print(f"[DEBUG] Agente {self.unique_id} no encuentra más fuego ni humo.")
                    break


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


    
    def break_wall(self, start, next):
        direction_sn = self.model.direction(start, next)
        direction_ns = self.model.direction(next, start)

        if direction_sn is not None:
            self.update_grid_walls(start, next, direction_sn, direction_ns)
            self.action_history.append(f"break wall:{start}-{next}")
            self.action_points -= 2
            self.model.damage_counter +=2


    # Cierra una puerta entre dos celdas
    # `x1` y `y1` son las celdas adyacentes donde se encuentra la puerta
    def close_door(self,x1, y1):
        if x1 in self.model.exit_positions and y1 in self.model.exit_positions:
            # Marca la puerta como cerrada en ambas posiciones
            self.model.exit_positions[x1] = False

            self.model.exit_positions[y1] = False

            # Registra la acción en el historial
            self.action_history.append(f"close door:{x1}-{y1}")

            # Resta 1 punto de acción por cerrar la puerta
            self.action_points -= 1

    def step(self):
        """Función que ejecuta el paso de un agente."""
        print(f"\n[DEBUG] Agente {self.unique_id} ({self.role}) inicia su turno en posición {self.pos}. Energía inicial: {self.action_points}.")
        
        self.model.log_event({
            "type": "agent_turn_start",
            "agent": self.unique_id,
            "role": self.role,
            "position": self.pos,
            "action_points": self.action_points
        })

        if self.role == "rescuer":
            self.rescuer_strategy()  # Ejecutar estrategia de rescate
        elif self.role == "firefighter":
            self.firefighter_strategy()  # Ejecutar estrategia de apagar incendios

        print(f"[DEBUG] Agente {self.unique_id} ({self.role}) termina su turno en posición {self.pos}. Energía restante: {self.action_points}.")
        
        self.model.log_event({
            "type": "agent_turn_end",
            "agent": self.unique_id,
            "role": self.role,
            "position": self.pos,
            "remaining_action_points": self.action_points
        })

        # Esparcir retratos (si es necesario) y fuego
        self.model.add_portraits()
        self.model.spread_boos()

        # Restaurar la energía para el próximo turno
        self.action_points += 4


    def toggle_point(self):
        """Método que permite al agente alternar entre llevar un retrato o no."""
        self.carrying_portrait = not self.carrying_portrait
        print(f"Agente {self.unique_id} ahora {'lleva un retrato' if self.carrying_portrait else 'no lleva un retrato'}.")

    
    # Abre una puerta entre dos celdas
    # `x1` y `y1` son las celdas adyacentes donde se encuentra la puerta
    def open_door(self,x1, y1):
        if x1 in self.model.exit_positions and y1 in self.model.exit_positions:
            # Marca la puerta como abierta en ambas posiciones
            self.model.exit_positions[x1] = True
            self.model.exit_positions[y1] = True

            # Registra la acción en el historial
            self.action_history.append(f"open door:{x1}-{y1}")

            # Resta 1 punto de acción por abrir la puerta
            self.action_points -= 1
