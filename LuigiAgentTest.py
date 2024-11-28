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
        # Obtiene la dirección entre las dos posiciones
        direction = self.model.direction(start, next)
        # Combina las posiciones para buscar en estructuras específicas
        combined_possn = start + next
        # Combina las posiciones en orden inverso
        combined_posns = next + start
        
        # Verifica si la celda inicial tiene información de paredes
        if start in self.model.grid_walls:
            # Determina si la pared en la dirección especificada está bloqueada
            wall_blocked = direction is not None and self.model.grid_walls[start][0][direction] == '1'
        else:
            # Si no hay datos, asume que no hay pared bloqueada
            wall_blocked = False

        # Si la combinación de posiciones está en las salidas, permite el paso
        if (combined_possn in self.model.exit_positions or 
            combined_posns in self.model.exit_positions):
            wall_blocked = False
        
        # Devuelve True si hay una pared bloqueada, False de lo contrario
        return wall_blocked

    # Verifica si hay una puerta cerrada entre dos posiciones
    def check_collision_doors(self, start, next):
        # Combina las posiciones para buscar salidas específicas
        combined_possn = start + next
        # Combina las posiciones en orden inverso
        combined_posns = next + start

        # Verifica si las posiciones están marcadas como salidas
        if combined_possn in self.model.exit_positions or \
           combined_posns in self.model.exit_positions:
            
            # Si ambas posiciones son salidas abiertas
            if self.model.exit_positions.get(combined_possn) and \
               self.model.exit_positions.get(combined_posns):
                # No hay puerta bloqueada
                doors_blocked = False

            else:
                # Hay una puerta bloqueada
                doors_blocked = True
        else:
            # No hay puerta en estas posiciones
            doors_blocked = False

        # Devuelve True si la puerta está cerrada, False de lo contrario
        return doors_blocked
    
    # Calcula una heurística basada en la distancia de Manhattan más un factor aleatorio
    def manhattan_heuristic(self, cell, goal):
        # Calcula la heurística Manhattan entre dos celdas

        # La distancia de Manhattan es la suma de las diferencias absolutas 
        # entre las coordenadas de las dos celdas
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]) + random.uniform(0, 0.5)
        # Se agrega un factor aleatorio para romper posibles empates

    # Mueve al agente hacia un objetivo utilizando el algoritmo Dijkstra
    def move_towards(self, target):
        # Si ya está en el objetivo, no necesita moverse
        if self.pos == target:
            return True
        
        # Calcula el camino más corto al objetivo
        path = self.dijkstra(self.model.grid_details, self.pos, [target])
        print(f"[DEBUG] Agente {self.unique_id} tiene el camino: {path}")
        # Si no hay camino, devuelve False

        if not path:
            print(f"[DEBUG] Agente {self.unique_id} no puede alcanzar el objetivo desde {self.pos}.")
            return False
        
        # Obtiene el siguiente paso del camino
        next_step = path[0]
        print(f"[DEBUG] Agente {self.unique_id} se mueve de {self.pos} a {next_step}.")

        # Registra el movimiento en el modelo
        self.model.log_event({
            "type": "agent_move",
            "agent": self.unique_id,
            "from": self.pos,
            "to": next_step,
        })

        # Actualiza la posición del agente en la cuadrícula
        self.model.grid.move_agent(self, next_step)
        # Actualiza la posición actual del agente
        self.pos = next_step
        # Registra la posición en el historial
        self.history.append(self.pos)

        # Resta puntos de acción, más si lleva un retrato
        self.action_points -= 2 if self.carrying_portrait else 1

        # Devuelve True para indicar que el movimiento fue exitoso
        return True

    # Examina un retrato en una posición y determina si es una víctima o una falsa alarma
    def examine_portrait(self, position):
        # Verifica si hay un retrato en la posición
        if position in self.model.portraits:
            # Obtiene el retrato en la posición
            portrait = self.model.portraits[position]
            # Si el retrato representa una víctima

            if portrait == "victim":
                # El agente ahora lleva el retrato
                self.carrying_portrait = True
                # Elimina el retrato de la posición
                self.model.portraits[position] = None

                print(f"Agente {self.unique_id} ha encontrado una víctima en {position}.")

                # Registra la acción
                self.action_history.append(f"Portrait found at: {position}, Type: Victim")

                # Registra el evento en el modelo
                self.model.log_event({
                    "type": "found_portrait",
                    "at": position,
                    "agent": self.unique_id,
                    "portrait_type": "victim",
                })

                # Devuelve los datos del retrato
                return {"position": position, "type": "victim"}
            
            # Si el retrato es una falsa alarma
            elif portrait == "false_alarm":
                # Elimina el retrato de la posición
                self.model.portraits[position] = None

                print(f"Agente {self.unique_id} encontró una falsa alarma en {position}.")

                self.action_history.append(f"Portrait found at: {position}, Type: False")
                # Registra el evento en el modelo

                self.model.log_event({
                    "type": "found_portrait",
                    "at": position,
                    "agent": self.unique_id,
                    "portrait_type": "False",
                })

                # Devuelve los datos del retrato
                return {"position": position, "type": "false_alarm"}
            
        # Devuelve None si no se encontró un retrato
        return None

    # Apaga un fuego en una posición específica si tiene suficientes puntos de acción
    def extinguish_fire(self, position):
        # Verifica si el agente tiene al menos 2 puntos de acción
        if self.action_points >= 2:
            print(f"[DEBUG] Agente: {self.unique_id} fuego apagado en {position}.")

            # Marca la celda como libre de fuego
            self.model.grid_details[position] = 0
            # Resta 2 puntos de acción
            self.action_points -= 2

            # Registra la acción en el historial
            self.action_history.append(f"Fire extinguished at: {position}") 

            # Registra el evento en el modelo
            self.model.log_event({
                    "type": "fire_extinguished",
                    "agent": self.unique_id,
                    "at": position,
                })
            
        # Si no tiene suficientes puntos de acción
        else:
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {position}.")

    # Intenta reducir o eliminar el humo en una celda específica
    # `position` es la celda objetivo
    # `reducing` indica si se está convirtiendo fuego en humo (True) o eliminando humo completamente (False)
    def extinguish_smoke(self, position, reducing):
        # Verifica si el agente tiene al menos 1 punto de acción.
        if self.action_points >= 1:
            print(f"[DEBUG] Agente {self.unique_id} eliminó el humo en {position}.")
            # Reduce el nivel de humo o fuego en la celda objetivo
            self.model.grid_details[position] -= 1
            # Resta 1 punto de acción al agente
            self.action_points -= 1

            # Caso en el que se está eliminando humo completamente
            if reducing == False:
                self.action_history.append(f"Smoke extinguished at: {position}")

                self.model.log_event({
                        "type": "fire_to_smoke",
                        "agent": self.unique_id,
                        "at": position,
                    })
                
            # Caso en el que se está reduciendo fuego a humo
            else:
                print(f"[DEBUG] Agente {self.unique_id} reduce el fuego a humo en {position}.")
                self.model.log_event({
                    "type": "smoke_extinguished",
                    "agent": self.unique_id,
                    "position": position,
                })

        else:
            # Si no tiene puntos de acción suficientes
            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar humo en {position}.")

    # Mueve al agente dentro de la cuadrícula central
    def move_inside_central_grid(self):
        # Si el agente está en el borde superior, se mueve hacia abajo
        if (self.pos[0] == 0):
            next_step = (1, self.pos[1])

        # Si está en el borde izquierdo, se mueve hacia la derecha
        elif (self.pos[1] == 0):
            next_step = (self.pos[0], 1)

        # Si está en el borde inferior, se mueve hacia arriba
        elif (self.pos[0] == self.model.grid.width - 1):
            next_step = (self.model.grid.width - 2, self.pos[1])

        # Si está en el borde derecho, se mueve hacia la izquierda
        elif (self.pos[1] == self.model.grid.height - 1):
            next_step = (self.pos[0], self.model.grid.height - 2)
        
        # Si hay fuego en la celda objetivo
        if self.model.grid_details[next_step] == 2:
            # Lo apaga
            self.extinguish_fire(next_step)

        # Marca al agente como dentro de la cuadrícula central
        self.in_central_grid = True
        # Resta 1 punto de acción por el movimiento
        self.action_points -= 1

        # Actualiza la posición del agente en el modelo
        self.model.grid.move_agent(self, next_step)
        # Actualiza la posición actual
        self.pos = next_step

        # Agrega la posición al historial
        self.history.append(self.pos)

        print(f"[DEBUG] Agente {self.unique_id} se mueve dentro del cuadrante central en {self.pos}.")
        self.model.log_event({
            "type": "agent_move",
            "from": self.pos,
            "agent": self.unique_id,
            "to": next_step,
        })

    
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


    # Estrategia del agente cuando su rol es "rescatista"
    def rescuer_strategy(self):
        # Mientras tenga puntos de acción disponibles
        while self.action_points > 0:
            # Si está en modo desarrollo
            if DEVELOPMENT:
                # Consume un punto y pasa al siguiente turno
                self.action_points -= 1
                continue

            # Si hay fuego cerca, lo apaga y pasa al siguiente turno
            if self.handle_fire_around():
                continue


            # Si el agente lleva un retrato
            if self.carrying_portrait:
                # Encuentra las salidas válidas en el modelo
                valid_exits = [pos for pos in self.model.entrances if isinstance(pos, tuple) and len(pos) == 2]
                if valid_exits:
                    # Encuentra la salida más cercana utilizando la heurística de Manhattan
                    nearest_exit = min(valid_exits, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} lleva retrato. Moviéndose hacia la salida más cercana: {nearest_exit}")
                    
                    # Revisa si hay fuego alrededor antes de moverse
                    if self.handle_fire_around():
                        continue
                    
                    # Verifica si hay una pared bloqueando el camino
                    if self.check_collision_walls(self.pos, nearest_exit):
                        # Si tiene suficientes puntos, rompe la pared
                        if self.action_points >= 2:
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_exit}. Rompiendo pared.")
                            self.break_wall(self.pos, nearest_exit)

                        # Si no tiene suficientes puntos, termina el turno
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                            break

                    # Verifica si hay una puerta cerrada bloqueando el camino
                    elif self.check_collision_doors(self.pos, nearest_exit):
                        # Si tiene suficientes puntos, abre la puerta
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

                        # Si no tiene suficientes puntos, termina el turno
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                            break

                    # Si llega a la salida
                    if self.pos == nearest_exit:
                        print(f"[DEBUG] Agente {self.unique_id} ha llegado a la salida con el retrato.")

                        # Suelta el retrato en la salida
                        self.carrying_portrait = False
                        # Incrementa el contador de rescates
                        self.model.rescued += 1

                        print(f"[DEBUG] Agente {self.unique_id} ha rescatado a una víctima. Total rescatados: {self.model.rescued}")

                        self.model.log_event({
                            "type": "rescued_portrait",
                            "agent": self.unique_id,
                            "position": nearest_exit,
                            "rescued": self.model.rescued,
                        })

                    # Si aún tiene suficientes puntos de acción, continúa moviéndose hacia la salida
                    if self.action_points >= 2:
                        self.move_towards(nearest_exit)

                    # Si no tiene puntos suficientes, termina el turno
                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para moverse hacia {nearest_exit}.")
                    
                    if self.action_points < 2:
                        break

                # Si no hay salidas válidas, termina el turno
                else:
                    print(f"[ERROR] No hay salidas válidas para el agente {self.unique_id}. Terminando turno.")
                    break 
            else:
                # Si el agente no lleva un retrato
                # Si no está en el área central, se mueve hacia ella
                if not self.in_central_grid:
                    self.move_inside_central_grid()

                else:
                    # Si ya está en el área central, busca el retrato más cercano
                    portraits = [
                        pos for pos, label in self.model.portraits.items()
                        if label in ["victim", "false_alarm"] and isinstance(pos, tuple) and len(pos) == 2
                    ]

                    if portraits:
                        # Encuentra el retrato más cercano utilizando la heurística de Manhattan
                        nearest_portrait = min(portraits, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                        
                        print(f"[DEBUG] Agente {self.unique_id} buscando retrato. Moviéndose hacia el retrato más cercano: {nearest_portrait}")
                        
                        # Revisa si hay fuego cerca antes de moverse
                        if self.handle_fire_around():
                            continue
                        
                        # Verifica si hay una pared bloqueando el camino al retrato
                        if self.check_collision_walls(self.pos, nearest_portrait):
                            # Si tiene suficientes puntos, rompe la pared
                            if self.action_points >= 2:
                                print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_portrait}. Rompiendo pared.")
                                self.break_wall(self.pos, nearest_portrait)
                            # Si no tiene suficientes puntos, termina el turno
                            else:
                                print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                                break

                        # Verifica si hay una puerta cerrada bloqueando el camino
                        elif self.check_collision_doors(self.pos, nearest_portrait):
                            # Si tiene suficientes puntos, abre la puerta
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
                                # Si no tiene suficientes puntos, termina el turno
                                print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para abrir la puerta.")
                                break
                        
                        # Intenta moverse hacia el retrato
                        if not self.move_towards(nearest_portrait):
                            break
                        
                        # Si llega al retrato, lo examina
                        if self.pos == nearest_portrait:
                            if not self.examine_portrait(nearest_portrait):
                                continue
                    else:
                        # Si no hay más retratos, termina el turno
                        print(f"[DEBUG] No hay más retratos para el agente {self.unique_id}. Terminando turno.")
                        break

    # Estrategia del agente cuando su rol es "bombero"
    def firefighter_strategy(self):
        # Se inicializa un conjunto para rastrear las posiciones visitadas por el agente
        visited_positions = set()

        # Mientras el agente tenga puntos de acción, continúa ejecutando la estrategia
        while self.action_points > 0:
            # Si estamos en modo de desarrollo, reduce los puntos de acción y continúa
            if DEVELOPMENT:
                self.action_points -= 1
                continue

            # Si el agente no está dentro de la cuadrícula central, lo mueve hacia allí
            if not self.in_central_grid:
                self.move_inside_central_grid()

            else:
                # Obtiene las celdas donde hay fuego (valor 2) o humo (valor 1)
                fire_cells = [pos for pos, value in self.model.grid_details.items() if value == 1 or value == 2]

                if fire_cells:
                    # Encuentra el fuego o humo más cercano utilizando la heurística de Manhattan
                    nearest_fire = min(fire_cells, key=lambda pos: self.manhattan_heuristic(self.pos, pos))
                    print(f"[DEBUG] Agente {self.unique_id} buscando fuego. Moviéndose hacia el fuego más cercano: {nearest_fire}")

                    # Marca la celda como visitada si aún no lo ha sido
                    if nearest_fire not in visited_positions:
                        visited_positions.add(nearest_fire)

                    # Verifica si hay fuego o humo en las celdas adyacentes y lo apaga si es posible
                    if self.handle_fire_around():
                        continue

                    # Si hay una pared entre la posición actual y el fuego más cercano, intenta romperla
                    if self.check_collision_walls(self.pos, nearest_fire):
                        if self.action_points >= 2:
                            print(f"[DEBUG] Agente {self.unique_id} encuentra una pared entre {self.pos} y {nearest_fire}. Rompiendo pared.")
                            self.break_wall(self.pos, nearest_fire)

                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para romper la pared.")
                            break

                    # Si hay una puerta cerrada entre la posición actual y el fuego más cercano, intenta abrirla
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

                    # Verifica si tiene suficientes puntos de acción para extinguir fuego o humo
                    fire_value = self.model.grid_details[nearest_fire]
                    if fire_value == 2 and self.action_points < 2:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para extinguir fuego.")
                        break

                    elif fire_value == 1 and self.action_points < 1:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para extinguir humo.")
                        break
                    
                     # Mueve al agente hacia el fuego más cercano; si no puede moverse, termina
                    if not self.move_towards(nearest_fire):
                        break

                    # Si el agente llega al fuego o humo, intenta extinguirlo
                    if self.pos == nearest_fire:
                        if fire_value == 2:
                            if self.action_points >= 2:
                                # Extingue el fuego completamente
                                self.extinguish_fire(nearest_fire)

                            elif self.action_points == 1:
                                # Reduce el fuego a humo si tiene pocos puntos
                                reducing = True
                                self.extinguish_smoke(nearest_fire, reducing)
                                print(f"[DEBUG] Agente {self.unique_id} bajando fuego a humo . El fuego es : {nearest_fire}")
                                self.action_history.append(f"Fire reduced to smoke at: {nearest_fire}")

                        elif fire_value == 1:
                            # Extingue el humo
                            reducing = False
                            self.extinguish_smoke(nearest_fire, reducing)
                        continue

                else:
                    # Si no se encuentran más fuegos ni humos, termina
                    print(f"[DEBUG] Agente {self.unique_id} no encuentra más fuego ni humo.")
                    break

    # Verifica si hay fuego o humo en las celdas vecinas y los apaga si es posible
    def handle_fire_around(self):
        # Obtiene las celdas vecinas usando la vecindad de Moore
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        
        for neighbor in neighbors:
            if neighbor in self.model.grid_details:
                if self.model.grid_details[neighbor] == 2:
                    # Si hay fuego en una celda vecina y tiene suficientes puntos, lo apaga
                    if self.action_points >= 2:
                        if not self.check_collision_walls(self.pos, neighbor):
                            self.extinguish_fire(neighbor)
                            return True
                        else:
                            # Si hay una pared entre el agente y el fuego, intenta romperla
                            self.break_wall(self.pos, neighbor)

                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar fuego en {neighbor}. Puntos disponibles: {self.action_points}")
                
                elif self.model.grid_details[neighbor] == 1:
                    # Si hay humo en una celda vecina y tiene suficientes puntos, lo apaga
                    if self.action_points >= 1:
                        if not self.check_collision_walls(self.pos, neighbor):
                            reducing = True
                            self.extinguish_smoke(neighbor,reducing)
                            return True
                        
                        else:
                            print(f"[DEBUG] Agente {self.unique_id} no puede romper paredes para apagar humo en {neighbor}.")

                    else:
                        print(f"[DEBUG] Agente {self.unique_id} no tiene suficientes puntos para apagar humo en {neighbor}. Puntos disponibles: {self.action_points}")
        # Retorna falso si no se logró apagar fuego o humo en las celdas vecinas
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
                "target": next,           # Registra la posición objetivo donde estaba la pared rota
                "damage":self.model.damage_counter  # Registra el contador de daños
            })

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