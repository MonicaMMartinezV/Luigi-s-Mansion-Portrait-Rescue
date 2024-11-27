import heapq
from mesa import Agent
from queue import Queue

import random

DEVELOPMENT = False

class LuigiAgent(Agent):
    """Agente que simula a Luigi en el modelo de rescate y bombero."""

    def __init__(self, unique_id, model, role, position):
        super().__init__(unique_id, model)
        self.role              = role  # rol: 'rescuer' o 'firefighter'
        self.pos               = None  # Posición del agente en el grid
        self.model             = model
        self.history           = []  # Histórico de movimientos
        self.action_history    = []  # Histórico de acciones
        self.action_points     = 4  # Puntos de acción para cada turno
        self.carrying_portrait = False  # Indica si el agente lleva un retrato (víctima)
        self.in_central_grid   = False  # Indica si el agente se encuentra dentro del grid central
        self.start_position    = position

    def reset(self):
        """Restaura el agente a su estado inicial."""
        self.carrying_portrait = False
        self.in_central_grid = False
        print(f"[DEBUG] Agente {self.unique_id} ha muerto.")

        # Si tiene una posición inicial definida, mover al agente allí
        if self.start_position:
            self.model.grid.move_agent(self, self.start_position)
            self.pos = self.start_position
            print(f"[DEBUG] Agente {self.unique_id} movido a su posición inicial {self.start_position}.")

    def heuristic(self, cell, goal):
        """Calcula la distancia Manhattan entre una celda y un objetivo."""
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]) + random.uniform(0, 0.5)
    
    def a_star(self, grid, ag, goals):
        open_list = [(0, ag)]  # priority queue
        closed_list = set()
        came_from = {}
        cost_so_far = {ag: 0}

        if len(goals) >= 1:
            while open_list:
                _, current = heapq.heappop(open_list)
                if current in goals:
                    path = []
                    while current in came_from:
                        path.append(current)
                        current = came_from[current]
                    return path[::-1]

                closed_list.add(current)
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:  # 4-neighbors
                    x, y = current[0] + dx, current[1] + dy
                    neighbor = (x, y)

                    if neighbor not in grid:
                        continue
                    if neighbor in closed_list:
                        continue

                    cost = grid[neighbor]
                    if self.check_collision_walls(current, neighbor):
                        cost += 4
                    if self.check_collision_doors(current, neighbor):
                        cost += 1

                    tentative_cost = cost_so_far[current] + cost

                    if neighbor not in cost_so_far or tentative_cost < cost_so_far[neighbor]:
                        cost_so_far[neighbor] = tentative_cost

                        # Verificar si hay un objetivo válido
                        valid_goals = [self.heuristic(neighbor, goal) for goal in goals]

                        if valid_goals:
                            priority = tentative_cost + min(valid_goals)
                        else:
                            # Si no hay objetivos válidos, usar la ubicación del agente
                            priority = tentative_cost + self.heuristic(neighbor, ag)

                        heapq.heappush(open_list, (priority, neighbor))
                        came_from[neighbor] = current
            return [ag]  # no path found
        else:
            return [ag]
    
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

        path = self.a_star(self.model.grid_details, self.pos, [target])
        print(f"[DEBUG] Agente {self.unique_id} tiene el camino: {path}")
        if not path:
            print(f"[DEBUG] Agente {self.unique_id} no puede alcanzar el objetivo desde {self.pos}.")
            return False  # No se encontró un camino

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
            print(f"[DEBUG] Agente: {self.unique_id} fuego apagado en {position}.")
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
            print(f"[DEBUG] Agente {self.unique_id} eliminó el humo en {position}.")
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

            # Apagar fuego o humo antes de moverse
            if self.handle_fire_around():
                continue  # Después de apagar fuego, vuelve a comenzar el turno

            if self.carrying_portrait:
                # Si lleva un retrato, moverse hacia la salida más cercana
                valid_exits = [pos for pos in self.model.entrances if isinstance(pos, tuple) and len(pos) == 2]
                if valid_exits:
                    nearest_exit = min(valid_exits, key=lambda pos: self.heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} lleva retrato. Moviéndose hacia la salida más cercana: {nearest_exit}")

                    # Apagar fuego o humo antes de moverse
                    if self.handle_fire_around():
                        continue  # Después de apagar fuego, vuelve a comenzar el turno
                    
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
                        nearest_portrait = min(portraits, key=lambda pos: self.heuristic(self.pos, pos))
                        print(f"[DEBUG] Agente {self.unique_id} buscando retrato. Moviéndose hacia el retrato más cercano: {nearest_portrait}")

                        # Apagar fuego o humo antes de moverse
                        if self.handle_fire_around():
                            continue  # Después de apagar fuego, vuelve a comenzar el turno
                        
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

                        if not self.move_towards(nearest_portrait):  # Si no puede moverse, detenerse
                            break
                        
                        # Verificar si llegó al retrato y procesarlo
                        if self.pos == nearest_portrait:
                            if not self.examine_portrait(nearest_portrait):  # Si no es una víctima, sigue buscando otro retrato
                                continue
                    else:
                        print(f"[DEBUG] No hay más retratos para el agente {self.unique_id}. Terminando turno.")
                        break

    def firefighter_strategy(self):
        """Estrategia para agentes cuyo rol es apagar incendios."""
        visited_positions = set()
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
                    nearest_fire = min(fire_cells, key=lambda pos: self.heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} buscando fuego. Moviéndose hacia el fuego más cercano: {nearest_fire}")

                    if nearest_fire not in visited_positions:
                        visited_positions.add(nearest_fire)

                    if self.handle_fire_around():
                        continue  # Después de apagar fuego/humo, vuelve a comenzar el turno

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
    
    def handle_fire_around(self):
        """Verifica si hay fuego o humo en las celdas vecinas y los apaga si es posible."""
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        for neighbor in neighbors:
            if neighbor in self.model.grid_details:
                # Verificar primero si el agente tiene puntos suficientes
                if self.model.grid_details[neighbor] == 2:  # Fuego
                    if self.action_points >= 2:
                        if not self.check_collision_walls(self.pos, neighbor):
                            self.extinguish_fire(neighbor)
                            return True  # Detenerse después de apagar fuego
                        else:
                            self.break_wall(self.pos, neighbor)
                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {neighbor}. Puntos disponibles: {self.action_points}")
                elif self.model.grid_details[neighbor] == 1:  # Humo
                    reducing = True
                    if self.action_points >= 1:
                        if not self.check_collision_walls(self.pos, neighbor):
                            self.extinguish_smoke(neighbor,reducing)
                            return True  # Detenerse después de apagar humo
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no puede romper paredes para apagar humo en {neighbor}.")
                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar humo en {neighbor}. Puntos disponibles: {self.action_points}")
        return False  # No se encontró fuego ni humo en las celdas vecinas

    def update_grid_walls(self, origin, target, direction_sn, direction_ns):
        origin_wall = list(self.model.grid_walls[origin][0])
        target_wall = list(self.model.grid_walls[target][0])
        origin_wall[direction_sn]= "0"
        target_wall[direction_ns]= "0"
        self.model.grid_walls[origin][0] = ''.join(origin_wall)
        self.model.grid_walls[target][0] = ''.join(target_wall)

    
    def break_wall(self, start, next):
        direction_sn = self.model.direction(start, next)
        direction_ns = self.model.direction(next, start)

        if direction_sn is not None:
            self.update_grid_walls(start, next, direction_sn, direction_ns)
            self.action_history.append(f"break wall:{start}-{next}")
            self.action_points -= 2
            self.model.damage_counter +=1
            print(f"[DEBUG] Agente {self.unique_id} rompió la pared {next}.")

    def open_door(self,coord1, coord2):
        if coord1 in self.model.exit_positions and coord2 in self.model.exit_positions:
            self.model.exit_positions[coord1] = True
            self.model.exit_positions[coord2] = True
            self.action_history.append(f"open door:{coord1}-{coord2}")
            self.action_points -= 1

    def close_door(self,coord1, coord2):
        if coord1 in self.model.exit_positions and coord2 in self.model.exit_positions:
            self.model.exit_positions[coord1] = False
            self.model.exit_positions[coord2] = False
            self.action_history.append(f"close door:{coord1}-{coord2}")
            self.action_points -= 1

    def step(self):
        """Función que ejecuta el paso de un agente."""
        print(f"\n[DEBUG] Agente {self.unique_id} ({self.role}) inicia su turno en posición {self.pos}. Energía inicial: {self.action_points}.")

        if self.role == "rescuer":
            self.rescuer_strategy()  # Ejecutar estrategia de rescate
        elif self.role == "firefighter":
            self.firefighter_strategy()  # Ejecutar estrategia de apagar incendios

        print(f"[DEBUG] Agente {self.unique_id} ({self.role}) termina su turno en posición {self.pos}. Energía restante: {self.action_points}.")

        # Esparcir retratos (si es necesario) y fuego
        self.model.add_portraits()
        self.model.spread_boos()

        # Restaurar la energía para el próximo turno
        self.action_points += 4


    def toggle_point(self):
        """Método que permite al agente alternar entre llevar un retrato o no."""
        self.carrying_portrait = not self.carrying_portrait
        print(f"Agente {self.unique_id} ahora {'lleva un retrato' if self.carrying_portrait else 'no lleva un retrato'}.")