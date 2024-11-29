from mesa import Model  # Define los agentes y el modelo base de la simulación
from mesa.space import MultiGrid  # Permite colocar los agentes en una cuadrícula (multi o individual)
from mesa.time import BaseScheduler
from mesa.datacollection import DataCollector  # Recolecta y organiza datos de la simulación para análisis
from LuigiAgentTest import LuigiAgent

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
        
        print(f"Corriendo con semilla: {seed}")

        # Variables iniciales del modelo

        # Contador de pasos en la simulación
        self.step_count        = 0
        # Planificador para manejar agentes
        self.schedule          = BaseScheduler(self)
        
        # Número de retratos rescatados
        self.rescued           = 0
        # Número de pérdidas durante la simulación
        self.losses            = 0


        # Número de víctimas
        self.casualties        = 0
        #self.saved_count      = 0
        # Estado inicial de la simulación
        self.simulation_status = "In progress"
        # Mensaje al finalizar la simulación
        self.simulation_end    = ""


        # Coordenadas de zonas de fantasmas
        self.boo_zones         = [(row, col) for col, row in boo]
        # Configuración de los muros
        self.wall_config       = walls
        # Modo de la simulación
        self.mode              = mode
        # Lista para almacenar eventos del modelo
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
            for y in range(1, self.grid_height)
            for x in range(1, self.grid_width)
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

        def adjust_position_outside_grid(x, y, grid_width, grid_height):
            # Ajusta la posición para que esté justo afuera del grid
            if y == 1:  # Borde superior
                return (x, 0)
            elif x == 1:  # Borde izquierdo
                return (0, y)
            elif x == grid_width - 2:  # Borde derecho
                return (grid_width - 1, y)
            elif y == grid_height - 2:  # Borde inferior
                return (x, grid_height - 1)
            return (x, y)  # Si no está en un borde, no se ajusta (esto no debería ocurrir)

        # Ajuste de las posiciones de las entradas fuera del grid
        adjusted_positions = [
            adjust_position_outside_grid(x, y, self.grid_width, self.grid_height) 
            for x, y in self.entrances
        ]

        # Crear un ciclo de roles alternados
        agent_roles = itertools.cycle(["rescuer", "firefighter"])

        # Agregar los agentes en las posiciones
        total_agents = luigis
        idx = 0  # Índice para los agentes

        # Asignar agentes a cada entrada
        for i, position in enumerate(adjusted_positions):
            if total_agents == 0:
                break  # Si no quedan más agentes, salir del bucle

            # Asignar un agente "rescuer" en esta posición
            role = "rescuer"
            agent = LuigiAgent(idx, self, role)
            agent.unique_id = idx
            self.grid.place_agent(agent, position)
            self.schedule.add(agent)
            print(f"Agente {idx} con rol {role} colocado en posición {position}")
            total_agents -= 1
            idx += 1  # Incrementar el índice de agente

            if total_agents == 0:
                break  # Si ya no quedan más agentes, salir del bucle

            # Asignar un agente "firefighter" en la siguiente posición, separada
            next_position = adjusted_positions[(i + 1) % len(adjusted_positions)]  # Usar la siguiente posición
            role = "firefighter"
            agent = LuigiAgent(idx, self, role)
            agent.unique_id = idx
            self.grid.place_agent(agent, next_position)
            self.schedule.add(agent)
            print(f"Agente {idx} con rol {role} colocado en posición {next_position}")
            total_agents -= 1
            idx += 1  # Incrementar el índice de agente

        # Si hay más agentes que posiciones de entrada
        if total_agents > 0:
            for _ in range(total_agents):
                position = adjusted_positions[idx % len(adjusted_positions)]
                role = next(agent_roles)
                agent = LuigiAgent(idx, self, role)
                agent.unique_id = idx
                self.grid.place_agent(agent, position)
                self.schedule.add(agent)
                print(f"Agente {idx} con rol {role} colocado en posición {position}")
                idx += 1




    def log_event(self, event):
        """Agrega un evento al registro del modelo."""
        self.model_events.append(event)

    def add_portraits(self):
        """Agrega retratos alternando entre víctimas y falsas alarmas hasta completar el total deseado."""
        total_victims = sum(1 for portrait in self.portraits.values() if portrait == "victim")
        total_false_alarms = sum(1 for portrait in self.portraits.values() if portrait == "false_alarm")

        max_victims = 10
        max_false_alarms = 5

        active_points = total_victims + total_false_alarms
        needed_points = 3 - active_points

        reduced = False
        new_points = 0

        # Definir el área central del grid
        central_area = [
            (x, y) for x in range(1, 9) for y in range(1, 7)
        ]

        # Alternar entre victim y false_alarm
        next_type = "victim" if total_victims <= total_false_alarms else "false_alarm"

        while new_points < needed_points:
            if total_victims >= max_victims and total_false_alarms >= max_false_alarms:
                break  # No agregar más si ambos tipos han alcanzado su límite

            candidate_point = random.choice(central_area)
            if candidate_point not in self.portraits:
                if self.grid_details.get(candidate_point) in [1, 2]:  # 1 para humo, 2 para fuego
                    # Eliminar fuego o humo y colocar el retrato en su lugar
                    self.grid_details[candidate_point] = 0  # Eliminar humo/fuego
                    reduced = True
                    print(f"[DEBUG] El fuego/humo en {candidate_point} fue removido para poner un retrato.")

                # Agregar el retrato del tipo correspondiente
                if next_type == "victim" and total_victims < max_victims:
                    self.portraits[candidate_point] = "victim"
                    total_victims += 1
                elif next_type == "false_alarm" and total_false_alarms < max_false_alarms:
                    self.portraits[candidate_point] = "false_alarm"
                    total_false_alarms += 1
                else:
                    continue  # Saltar si no es posible añadir el tipo actual

                self.grid_details[candidate_point] = 0
                new_points += 1
                print(f"[INFO] Nuevo retrato agregado en {candidate_point}: {self.portraits[candidate_point]}")
                self.log_event({
                    "type": "portrait_added",
                    "position": candidate_point,
                    "portrait_type": self.portraits[candidate_point],
                    "step": self.step_count
                })

                # Alternar el tipo para el siguiente retrato
                next_type = "victim" if next_type == "false_alarm" else "false_alarm"

        if reduced:
            self.log_event({
                "type": "fire_removed_to_portrait",
                "position": candidate_point,
                "portrait_type": self.portraits[candidate_point],
                "step": self.step_count
            })


    def spread_boos(self):
        """Extiende la presencia de fantasmas únicamente dentro del área central del grid."""
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
                    "type": "smoke_to_fire",
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
                                if self.grid_details.get(neighbor) == 0:
                                    print(f"[INFO] Nuevo fuego extendido de {target_pos} a {neighbor}")
                                    self.log_event({
                                        "type": "fire_extended",
                                        "from": target_pos,
                                        "to": neighbor,
                                        "step": self.step_count
                                    })
                                else:
                                    self.log_event({
                                    "type": "smoke_to_fire",
                                    "position": target_pos,
                                    "step": self.step_count
                                })
                                self.grid_details[neighbor] = 2
                                self.boo_zones.append(neighbor)
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


    # Registra daño en muros o puertas entre dos celdas del grid                      
    def register_damage_walls_doors(self, origin, target):
        # Si ambas posiciones son puertas y están cerradas (False en self.exit_positions)
        if origin in self.exit_positions and target in self.exit_positions:
            
            
            if self.exit_positions[origin]==False and self.exit_positions[target]==False:
                
                # Eliminar ambas puertas de la lista de puertas activas
                del self.exit_positions[origin]

                del self.exit_positions[target]
                
                
                # Obtener las configuraciones de muros de ambas posiciones
                # Muro de origen
                origin_wall = list(self.grid_walls[origin][0])

                # Muro de destino
                target_wall = list(self.grid_walls[target][0])


                # Determinar las direcciones relativas entre origen y destino
                # Dirección del muro en origen
                path_org = self.direction(origin, target)

                # Dirección del muro en destino
                path_targ = self.direction(target, origin)


                # Marcar las paredes como destruidas (0 indica muro destruido)
                origin_wall[path_org] = "0"

                target_wall[path_targ] = "0"
                

                # Actualizar las configuraciones de muros en el grid
                self.grid_walls[origin][0] = "".join(origin_wall)

                # Incrementar el contador de daño total
                self.grid_walls[target][0] = "".join(target_wall)
                self.damage_counter += 1
        else:
            # Definir el área central del grid para limitar la acción
            central_area = [
                (x, y) for x in range(1, 9) for y in range(1, 7)
            ]
            
            # Si el objetivo está dentro del área central
            if target in central_area:
                # Determinar direcciones entre origen y destino
                path_org= self.direction(origin, target)
                # `path_org` representa la dirección relativa desde la celda `origin` hacia la celda `target`
                # Por ejemplo, si `origin` está al norte de `target`, `path_org` será 2 (indicando dirección sur)

                # `path_targ` representa la dirección relativa desde la celda `target` hacia la celda `origin`
                # Este valor es complementario al de `path_org`. Por ejemplo, si `path_org` es 2 (sur), `path_targ` será 0 (norte)
                path_targ= self.direction(target, origin)

                # Obtener muros y contadores de daños para origen y destino
                origin_wall = list(self.grid_walls[origin][0])
                # `origin_wall` es una lista que indica el estado de los muros en la celda `origin`
                # Cada posición de la lista (0 a 3) corresponde a una dirección cardinal:
                # - 0: Norte
                # - 1: Este
                # - 2: Sur
                # - 3: Oeste
                # El valor "1" significa que hay un muro presente, y "0" significa que el muro está destruido
                
                # Obtener la configuración de los muros en la celda de destino
                target_wall = list(self.grid_walls[target][0])
                # `target_wall` funciona igual que `origin_wall`, pero para la celda `target`
                
                
                # Obtener los contadores de daño en la celda de origen
                origin_counter = list(self.grid_walls[origin][1])
                # `origin_counter` es una lista que indica si un muro en `origin` ha recibido daño:
                # - "0": No ha recibido daño
                # - "1": Ha recibido daño pero aún no está destruido

                # Obtener los contadores de daño en la celda de destino
                target_counter = list(self.grid_walls[target][1])
                # `target_counter` funciona igual que `origin_counter`, pero para la celda `target`
                
                # Caso: Ambas celdas ya tienen el muro marcado como dañado ("1")
                if origin_counter[path_org]== "1" and target_counter[path_targ]== "1":
                    # Verifica si ambos lados del muro (en `origin` y `target`) ya tienen daño registrado
                    
                    # Incrementa el contador global de daño en el modelo, que registra cuántos muros han sido destruidos o dañados
                    self.damage_counter += 1
                    
                    # Actualiza el muro en `origin` para marcarlo como destruido (cambiar "1" a "0")
                    origin_wall[path_org]= "0"

                    # Actualiza el muro en `target` para marcarlo como destruido (cambiar "1" a "0")
                    target_wall[path_targ]= "0"
                    
                    # Convierte la lista de `origin_wall` nuevamente en una cadena y la guarda en `self.grid_walls[origin][0]`.
                    # Esto asegura que el estado del muro en `origin` quede registrado correctamente en el modelo.
                    self.grid_walls[origin][0] = ''.join(origin_wall)
                    
                    # Convierte la lista de `target_wall` nuevamente en una cadena y la guarda en `self.grid_walls[target][0]`.
                    # Esto asegura que el estado del muro en `target` quede registrado correctamente en el modelo.
                    self.grid_walls[target][0] = ''.join(target_wall)
                    
                    print(f"[INFO] Pared destruida de {origin} a {target}")
                    
                    self.log_event({
                        "type": "wall_destroyed",
                        "position": origin,
                        "target": target,
                        "step": self.step_count
                    })

                # Caso: Ninguna celda tiene daño registrado previamente
                elif origin_counter[path_org]== "0" and target_counter[path_targ]== "0":
                    # Incrementar daño total
                    self.damage_counter += 1

                    # Registrar daño en origen
                    origin_counter[path_org] = "1"

                    # Registrar daño en destino
                    target_counter[path_targ] = "1"

                    # Actualizar contadores de daño en el grid
                    self.grid_walls[origin][1] = ''.join(origin_counter)


                    self.grid_walls[target][1] = ''.join(target_counter)
                    print(f"[INFO] Daño registrado en {origin} y {target}")
                    
                    self.log_event({
                        "type": "damage_wall",
                        "position": origin,
                        "target":target,
                        "step": self.step_count,
                        "damage":self.damage_counter
                    })
                else:
                    pass
            # Caso: La celda objetivo está fuera del área central
            else:
                # Determinar dirección entre origen y destino
                direction = self.direction(origin, target)

                # Definir coordenadas de las esquinas del grid
                origin_nw_crnr = (1,1) # Esquina noroeste
                origin_ne_crnr = (8,1) # Esquina noreste
                origin_sw_crnr = (1,6) # Esquina suroeste
                origin_sw_crnr = (8,6) # Esquina sureste
                
                # Validar si la posición está en una esquina específica y no en la dirección opuesta
                if origin == origin_nw_crnr or origin == origin_ne_crnr:
                    
                    # Dirección prohibida para estas esquinas
                    if direction != 0:
                        self.wall_damage(origin, target)
                
                elif origin == origin_sw_crnr or origin == origin_ne_crnr:
                    
                    # Dirección prohibida para estas esquinas
                    if direction != 2:
                        self.wall_damage(origin, target)

                # Caso general: Ni origen ni destino son entradas
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
        # Expandir incendios: convertir humo en fuego si hay fuego en vecinos
        smoke_cells = [pos for pos, val in self.grid_details.items() if val == 1]
        for smoke_cell in smoke_cells:
            neighbors = self.grid.get_neighborhood(smoke_cell, moore=False, include_center=False)
            for neighbor in neighbors:
                if self.grid_details[neighbor] == 2:  # Si hay fuego en un vecino
                    self.grid_details[smoke_cell] = 2  # Convertir el humo en fuego
                    break

        # Procesar puntos con retratos afectados por el fuego
        for point in list(self.portraits):
            if self.grid_details[point] == 2:  # Si hay fuego en el punto del retrato
                portrait_type = self.portraits[point]
                del self.portraits[point]  # Eliminar el retrato
                if portrait_type == "victim":  # Incrementar bajas solo si es víctima
                    self.casualties += 1
                    self.log_event({
                        "type": "portrait_lost",
                        "position": point,
                        "portrait_type": portrait_type,
                        "step": self.step_count
                    })
                    break

    def update_simulation_status(self):
        """Actualiza el estado de la simulación."""
        if self.casualties >= 4 or self.damage_counter >= 24:
            self.simulation_status = "Defeat"
            if self.casualties >=4:
                self.simulation_end = "Defeat by dead victims"
            if self.damage_counter >=24:
                self.simulation_end = "Defeat by damage"
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
        self.update_simulation_status()