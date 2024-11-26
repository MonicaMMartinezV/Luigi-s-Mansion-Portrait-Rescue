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

                    if self.check_collision_walls(current, neighbor):
                        continue

                    if neighbor not in grid:
                        continue
                    if neighbor in closed_list:
                        continue
                    cost = grid[neighbor]

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

        wall_blocked = direction != None and self.model.grid_walls[start][0][direction] == '1'
        
        if (combined_possn in self.model.exit_positions or \
            combined_posns in self.model.exit_positions):
            wall_blocked = False
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
        print(f"Agente {self.unique_id} tiene el camino: {path}")
        if not path:
            print(f"Agente {self.unique_id} no puede alcanzar el objetivo desde {self.pos}.")
            return False  # No se encontró un camino

        next_step = path[0]
        print(f"Agente {self.unique_id} se mueve de {self.pos} a {next_step}.")
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
                return {"position": position, "type": "victim"}  # Retorna detalles
            elif portrait == "false_alarm":
                self.model.portraits[position] = None  # Eliminar la falsa alarma
                print(f"Agente {self.unique_id} encontró una falsa alarma en {position}.")
                self.action_history.append(f"Portrait found at: {position}, Type: False")
                return {"position": position, "type": "false_alarm"}  # Retorna detalles
        return None  # Si no hay retrato en esa posición

    def extinguish_fire(self, position):
        """Extinguir fuego en la posición dada."""
        if self.action_points >= 2:
            print(f"[DEBUG] Agente {self.unique_id} apagando fuego en {position}.")
            self.model.grid_details[position] = 0  # Actualizar la celda a estado vacío
            self.action_points -= 2  # Reducir puntos de acción
            self.action_history.append(f"Fire extinguished at: {position}") 
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {position}.")

    def extinguish_smoke(self, position):
        """Extinguir humo en la posición dada."""
        if self.action_points >= 1:
            print(f"[DEBUG] Agente {self.unique_id} eliminando humo en {position}.")
            self.model.grid_details[position] -= 1   # Actualizar la celda a estado vacío
            self.action_points -= 1  # Reducir puntos de acción
            self.action_history.append(f"Smoke extinguished at: {position}") 
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar humo en {position}.")

    def move_inside_cntral_grid(self):
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
                    nearest_exit = min(valid_exits, key=lambda pos: self.heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} lleva retrato. Moviéndose hacia la salida más cercana: {nearest_exit}")
                    if not self.move_towards(nearest_exit):  # Detenerse si no puede moverse
                        print(f"[DEBUG] Agente {self.unique_id} no puede moverse hacia {nearest_exit}.")
                        break

                     # Si el agente llega a la salida, se rescató la víctima
                    if self.pos == nearest_exit:
                        print(f"[DEBUG] Agente {self.unique_id} ha llegado a la salida con el retrato.")
                        self.carrying_portrait = False  # Resetear estatus de
                        self.model.rescued += 1  # Contar el rescate en el modelo
                        print(f"[DEBUG] Agente {self.unique_id} ha rescatado a una víctima. Total rescatados: {self.model.rescued}")

                else:
                    print(f"[ERROR] No hay salidas válidas para el agente {self.unique_id}. Terminando turno.")
                    break 
            else:
                if not self.in_central_grid:
                    self.move_inside_cntral_grid()
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
        while self.action_points > 0:
            if DEVELOPMENT:
                self.action_points -= 1
                continue

            if not self.in_central_grid:
                self.move_inside_cntral_grid()
            else:
                # Buscar la celda más cercana con humo (valor 1) o fuego (valor 2)
                fire_cells = [pos for pos, value in self.model.grid_details.items() if value == 1 or value == 2]
                if fire_cells:
                    nearest_fire = min(fire_cells, key=lambda pos: self.heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} buscando fuego. Moviéndose hacia el fuego más cercano: {nearest_fire}")
                    if not self.move_towards(nearest_fire):  # Si no puede moverse hacia el fuego, detenerse
                        break
                    # Verificar si llegó al humo/fuego y procesarlo
                    if self.pos == nearest_fire:
                        fire_value = self.model.grid_details[nearest_fire]
                        if fire_value == 2 and self.action_points >= 2: # Si es fuego
                            # Dependiendo de puntos, extinguir o reducir a humo
                            self.extinguish_fire(nearest_fire)
                        elif fire_value == 1 and self.action_points >= 1: # Si tiene puntos y es humo
                            self.extinguish_smoke(nearest_fire)     
                        continue # Después de lidiar con el humo/fuego, sigue buscando otro
                else:
                    # Si no hay fuego, el bombero se detiene
                    print(f"[DEBUG] Agente {self.unique_id} no encuentra más fuego ni humo.")
                    break

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
        
        # Esparcir fuego
        self.model.spread_boos()

        # Restaurar la energía para el próximo turno
        self.action_points += 4


    def toggle_point(self):
        """Método que permite al agente alternar entre llevar un retrato o no."""
        self.carrying_portrait = not self.carrying_portrait
        print(f"Agente {self.unique_id} ahora {'lleva un retrato' if self.carrying_portrait else 'no lleva un retrato'}.")