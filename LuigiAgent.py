from mesa import Agent
from queue import Queue
from AStar import AStarSolver

DEVELOPMENT = False

class LuigiAgent(Agent):
    """Agente que simula a Luigi en el modelo de rescate y bombero."""

    def __init__(self, unique_id, model, role):
        super().__init__(unique_id, model)
        self.role              = role  # rol: 'rescuer' o 'firefighter'
        self.pos               = None  # Posición del agente en el grid
        self.model             = model
        self.history           = []  # Histórico de movimientos
        self.action_points     = 4  # Puntos de acción para cada turno
        self.carrying_portrait = False  # Indica si el agente lleva un retrato (víctima)
        self.in_central_grid   = False  # Indica si el agente se encuentra dentro del grid central

    def manhattan(self, target):
        """Calcula la distancia Manhattan entre el agente y el objetivo."""
        if not isinstance(target, tuple) or len(target) != 2:
            raise ValueError(f"Target inválido para cálculo de Manhattan: {target}")
        x, y = self.pos
        tx, ty = target
        return abs(x - tx) + abs(y - ty)

    def move_towards(self, target):
        """Mueve al agente hacia una celda objetivo usando la distancia Manhattan."""
        if self.pos == target:
            return True  # El agente ya está en la celda objetivo
        
        def get_adjacent_positions(pos):
            """Devuelve posiciones adyacentes válidas alrededor de `pos`."""
            x, y = pos
            possible_moves = [
                (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)
            ]

            # Filtrar solo las posiciones dentro de los límites del grid
            return [
                (nx, ny) for nx, ny in possible_moves
                if 0 <= nx < self.model.grid.width and 0 <= ny < self.model.grid.height and self.model.grid.is_cell_empty((nx, ny))
            ]

        # Implementar búsqueda en amplitud (BFS) para encontrar un camino
        visited = set()
        queue = Queue()
        queue.put((self.pos, []))  # (posición actual, camino hasta ahora)

        while not queue.empty():
            current_pos, path = queue.get()
            
            if current_pos in visited:
                continue
            
            visited.add(current_pos)

            for next_pos in get_adjacent_positions(current_pos):
                if next_pos == target:
                    path.append(next_pos)
                    break  # Encontramos el objetivo

                if next_pos not in visited:
                    queue.put((next_pos, path + [next_pos]))
            
            if path and path[-1] == target:
                break  # Finalizar la búsqueda cuando se encuentre un camino al objetivo

        # Verificar si el agente tiene suficiente energía para moverse
        if self.carrying_portrait and self.action_points < 2:
            print(f"Agente {self.unique_id} no tiene suficientes puntos de acción para moverse mientras carga un retrato.")
            return False  # No hay suficientes puntos para moverse con el retrato

        elif not self.carrying_portrait and self.action_points < 1:
            print(f"Agente {self.unique_id} no tiene suficientes puntos de acción para moverse.")
            return False  # No hay suficientes puntos para moverse sin el retrato

        # Si se encontró un camino, moverse hacia el primer paso del camino
        if path:
            next_step = path[0]
            print(f"Agente {self.unique_id} se mueve de {self.pos} a {next_step}.")
            self.model.grid.move_agent(self, next_step)
            self.pos = next_step
            self.history.append(self.pos)

            if self.carrying_portrait:
                self.action_points -= 2
            else: 
                self.action_points -= 1
            return True
        else:
            print(f"Agente {self.unique_id} no puede alcanzar el objetivo desde {self.pos}.")
            return False  # No se encontró un camino válido

    def examine_portrait(self, position):
        """Recoge el retrato de la víctima cuando el agente llega a su posición.
        Examina el retrato y determina si es una víctima o una falsa alarma.
        """
        if position in self.model.portraits:
            portrait = self.model.portraits[position]
            if portrait == "victim":
                self.carrying_portrait = True  # El agente ahora lleva un retrato (víctima)
                #self.model.saved_count += 1
                self.model.portraits[position] = None  # Eliminar la víctima rescatada
                print(f"Agente {self.unique_id} ha encontrado una víctima en {position}.")
            elif portrait == "false_alarm":
                print(f"Agente {self.unique_id} encontró una falsa alarma en {position}. Eliminando de la lista y buscando otro retrato.")
                self.model.portraits[position] = None  # Eliminar la falsa alarma
                return False  # Indicar que debe buscar otro retrato
        return True

    def extinguish_fire(self, position):
        """Extinguir fuego en la posición dada."""
        if self.action_points >= 2:
            print(f"[DEBUG] Agente {self.unique_id} apagando fuego en {position}.")
            self.model.grid_details[position] = 0  # Actualizar la celda a estado vacío
            self.action_points -= 2  # Reducir puntos de acción
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {position}.")

    def extinguish_smoke(self, position):
        """Extinguir humo en la posición dada."""
        if self.action_points >= 1:
            print(f"[DEBUG] Agente {self.unique_id} eliminando humo en {position}.")
            self.model.grid_details[position] -= 1   # Actualizar la celda a estado vacío
            self.action_points -= 1  # Reducir puntos de acción
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
                    nearest_exit = min(valid_exits, key=self.manhattan)
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
                        nearest_portrait = min(portraits, key=self.manhattan)
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
                    nearest_fire = min(fire_cells, key=self.manhattan)
                    print(f"[DEBUG] Agente {self.unique_id} buscando fuego. Moviéndose hacia el fuego más cercano: {nearest_fire}")
                    if not self.move_towards(nearest_fire):  # Si no puede moverse hacia el fuego, detenerse
                        break
                    # Verificar si llegó al humo/fuego y procesarlo
                    if self.pos == nearest_fire:
                        fire_value = self.model.grid_details[nearest_fire]
                        if fire_value == 2: # Si es fuego
                            # Dependiendo de puntos, extinguir o reducir a humo
                            if self.action_points >= 2:
                                self.extinguish_fire(nearest_fire)
                            elif self.action_points == 1:
                                self.extinguish_smoke(nearest_fire)
                        elif fire_value == 1: # Si tiene puntos y es humo
                            self.extinguish_smoke(nearest_fire)     
                        continue # Después de lidiar con el humo/fuego, sigue buscando otro
                else:
                    # Si no hay fuego, el bombero se detiene
                    print(f"[DEBUG] Agente {self.unique_id} no encuentra más fuego ni humo.")
                    break

    def step(self):
        """Función que ejecuta el paso de un agente."""
        print(f"\n[DEBUG] Agente {self.unique_id} ({self.role}) inicia su turno en posición {self.pos}. Energía inicial: {self.action_points}.")
        
        if self.role == "rescuer":
            self.rescuer_strategy()  # Ejecutar estrategia de rescate
        elif self.role == "firefighter":
            self.firefighter_strategy()  # Ejecutar estrategia de apagar incendios

        print(f"[DEBUG] Agente {self.unique_id} ({self.role}) termina su turno en posición {self.pos}. Energía restante: {self.action_points}.")
        
        # Restaurar la energía para el próximo turno
        self.action_points += 4


    def toggle_point(self):
        """Método que permite al agente alternar entre llevar un retrato o no."""
        self.carrying_portrait = not self.carrying_portrait
        print(f"Agente {self.unique_id} ahora {'lleva un retrato' if self.carrying_portrait else 'no lleva un retrato'}.")