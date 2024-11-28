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
                "Grid": "get_grid",             # Información del grid actual
                "Walls": "get_walls",           # Configuración de muros
                "Steps": "step_count",          # Contador de pasos
                "Doors": "doors",               # Puertas del grid
                "Damage": "damage_counter",     # Daño acumulado
                "Status": "simulation_status",  # Estado de la simulación
                "Portraits": "portraits",       # Información de retratos
                "Rescued": "rescued",           # Número de retratos rescatados
                "Losses": "losses"              # Número de pérdidas
            },
            agent_reporters={
                "Agent_ID": lambda agent: agent.unique_id,
                "Role": lambda agent: agent.role,
                "Position": lambda agent: (agent.pos[0], agent.pos[1]),
                "Agent History": lambda agent: getattr(agent, 'history', [])
            }
        )

        # Configuración inicial de retratos
        self.portraits = {}

        for (row, col) in fake_alarms:
            # Configurar alarmas falsas en el grid
            self.portraits[(int(col), int(row))] = "false_alarm"

        for (row, col) in victims:
            # Configurar víctimas en el grid
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

        # Definir función para imprimir todas las coordenadas del grid
        def print_grid_coordinates(grid_width, grid_height):
            print("\n--- Coordenadas del Grid ---")

            for y in range(grid_height):
                row = ""

                for x in range(grid_width):
                    # Ajustar el ancho de cada celda para alinear
                    row += f"({x},{y})".ljust(10)

                print(row)
            print("\n")

        # Crear el espacio y los detalles del grid
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        
        # Inicializar celdas con valor 0
        self.grid_details = {(x, y): 0 for y in range(self.grid_height) for x in range(self.grid_width)}
        
        # Contador de daño acumulado
        self.damage_counter = 0

        # Imprimir las coordenadas del grid
        print_grid_coordinates(self.grid_width, self.grid_height)

      # Inicializar el grid de muros respetando el rango válido
        self.grid_walls = {
            # Cada celda tiene una configuración de muro inicial
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

        # Definir función para ajustar posiciones fuera del grid
        def adjust_position_outside_grid(x, y, grid_width, grid_height):
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
            agent = LuigiAgent(idx, self, role, position)
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

            agent = LuigiAgent(idx, self, role, next_position)
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

                agent = LuigiAgent(idx, self, role, position)
                agent.unique_id = idx

                self.grid.place_agent(agent, position)
                self.schedule.add(agent)

                print(f"Agente {idx} con rol {role} colocado en posición {position}")
                idx += 1



    # Agrega un evento al registro del modelo
    def log_event(self, event):
        self.model_events.append(event)

    # Agrega retratos alternando entre víctimas y falsas alarmas hasta completar el total deseado
    def add_portraits(self):
        # Contar el número total de víctimas y falsas alarmas ya presentes en el grid
        total_victims = sum(1 for portrait in self.portraits.values() if portrait == "victim")
        total_false_alarms = sum(1 for portrait in self.portraits.values() if portrait == "false_alarm")

        # Definir límites máximos de víctimas y falsas alarmas
        max_victims = 10
        max_false_alarms = 5

        # Calcular puntos activos y los necesarios para alcanzar el objetivo
        active_points = total_victims + total_false_alarms
        needed_points = 3 - active_points

        # Bandera para rastrear si se eliminó fuego o humo
        reduced = False
        # Contador de nuevos retratos agregados
        new_points = 0

        # Definir el área central del grid donde se colocarán los retratos
        central_area = [
            (x, y) for x in range(1, 9) for y in range(1, 7)
        ]

        # Determinar el próximo tipo de retrato a agregar, alternando entre víctimas y falsas alarmas
        next_type = "victim" if total_victims <= total_false_alarms else "false_alarm"

        # Bucle para agregar retratos hasta alcanzar los puntos necesarios
        while new_points < needed_points:
            # Si ambos tipos alcanzaron su límite, detener el bucle
            if total_victims >= max_victims and total_false_alarms >= max_false_alarms:
                break  # No agregar más si ambos tipos han alcanzado su límite
            
            # Elegir una posición candidata al azar dentro del área central
            candidate_point = random.choice(central_area)
            if candidate_point not in self.portraits:
                # Si hay humo o fuego en la posición, eliminarlo antes de colocar un retrato
                
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

                # Actualizar detalles del grid y contar el nuevo retrato
                self.grid_details[candidate_point] = 0
                new_points += 1
                
                print(f"[INFO] Nuevo retrato agregado en {candidate_point}: {self.portraits[candidate_point]}")
                
                self.log_event({
                    "type": "portrait_added",
                    "position": candidate_point,
                    "portrait_type": self.portraits[candidate_point],
                    "step": self.step_count
                })

                # Alternar el tipo de retrato para el próximo ciclo
                next_type = "victim" if next_type == "false_alarm" else "false_alarm"
        
        # Registrar un evento si se eliminó fuego o humo para agregar un retrato
        if reduced:
            
            self.log_event({
                "type": "fire_removed_to_portrait",
                "position": candidate_point,
                "portrait_type": self.portraits[candidate_point],
                "step": self.step_count
            })

    # Extiende la presencia de fantasmas únicamente dentro del área central del grid
    def spread_boos(self):
        # Definir el área central del grid
        central_area = [
            (x, y) for x in range(1, 9) for y in range(1, 7)
        ]

        # Filtrar posiciones afectadas dentro del área central
        affected_positions = [
            pos for pos in central_area if self.grid_details.get(pos) in (0, 1, 2)
        ]
        
        if affected_positions:
            # Elegir una posición aleatoria dentro de las posiciones afectadas
            target_pos = random.choice(affected_positions)
            
            # Si la posición está vacía, agregar humo
            if self.grid_details[target_pos] == 0:
                self.grid_details[target_pos] = 1
                
                print(f"[INFO] Nuevo humo agregado en {target_pos}")
                
                self.log_event({
                    "type": "smoke_added",
                    "position": target_pos,
                    "step": self.step_count
                })
            
            # Si hay humo, convertirlo en fuego
            elif self.grid_details[target_pos] == 1:
                self.grid_details[target_pos] = 2
                
                print(f"[INFO] Nuevo fuego agregado en {target_pos}")
                
                self.log_event({
                    "type": "smoke_to_fire",
                    "position": target_pos,
                    "step": self.step_count
                })

            # Si hay fuego, extenderlo a vecinos
            elif self.grid_details[target_pos] == 2:
                neighbors = self.grid.get_neighborhood(target_pos, moore=False, include_center=False)
                
                for neighbor in neighbors:
                    if neighbor in central_area:
                        
                        # Verificar colisiones con muros o puertas
                        if self.grid_details.get(neighbor) == 0 or \
                           self.grid_details.get(neighbor) == 1:
                            
                            if self.check_collision_walls_doors(target_pos, neighbor):
                                self.register_damage_walls_doors(target_pos, neighbor)
                            
                            else:
                                # Extender el fuego al vecino
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
    
    # Aplica daño a un muro específico entre dos celdas
    def wall_damage(self, origin, target):
        # Determinar dirección del muro a partir de origen y destino
        path_org       = self.direction(origin, target)

        # Obtener muros y contadores de daño de la celda origen
        origin_wall    = list(self.grid_walls[origin][0])

        # Caso: El muro ya estaba dañado ("1"), se destruye completamente
        origin_counter = list(self.grid_walls[origin][1])
        if origin_counter[path_org]== "1":
            # Incrementar contador de daño
            self.damage_counter += 1
            # Marcar muro como destruido
            origin_wall[path_org]= "0"

            # Actualizar el grid
            self.grid_walls[origin][0] = ''.join(origin_wall)
            print(f"[INFO] Pared destruida de {origin} a {target}")
            self.log_event({
                "type": "wall_destroyed",
                "position": origin,
                "target": target,
                "step": self.step_count
            })

        # Caso: El muro estaba intacto ("0"), se marca como dañado
        elif origin_counter[path_org]== "0":
            # Incrementar contador de daño
            self.damage_counter += 1

            # Registrar daño en el muro
            origin_counter[path_org] = "1"
            
            # Actualizar contador en el grid
            self.grid_walls[origin][1] = ''.join(origin_counter)
            print(f"[INFO] Daño registrado en {origin}")
            self.log_event({
                "type": "damage_wall",
                "position": origin,
                "target":origin,
                "step": self.step_count,
                "damage":self.damage_counter
            })
        else:
            pass

    # Maneja la dinámica de explosiones desde una celda específica
    # Las explosiones dañan paredes, se propagan a celdas vecinas y pueden causar daño estructural
    def trigger_explosion(self, origin, target):
        print(f"[DEBUG] Explosión iniciada en {origin} con dirección a {target}.")
        
        # Determina la dirección de la explosión desde la celda de origen hacia la celda objetivo
        direction = self.direction(origin, target)

        # Obtiene las celdas vecinas del objetivo dentro de la vecindad de Von Neumann (moore=False)
        exp_neighbors = self.grid.get_neighborhood(target, moore=False, include_center=False)
        
        # Itera sobre cada vecino de la celda objetivo para procesar los efectos de la explosión
        for exp_neighbor in exp_neighbors:
            
            # Verifica si el vecino está en la misma dirección que la explosión y no es la celda de origen  
            if self.direction(target, exp_neighbor) == direction and \
               exp_neighbor != origin:
                
                # Si hay una colisión con muros o puertas entre las celdas objetivo y vecina
                if self.check_collision_walls_doors(target, exp_neighbor):
                    # Registra el daño en el muro o puerta
                    self.register_damage_walls_doors(target, exp_neighbor)
                    break # Detiene la propagación en esa dirección

                # Si la celda vecina está vacía (0) o contiene humo (1)
                elif self.grid_details.get(exp_neighbor) == 0 or \
                   self.grid_details.get(exp_neighbor) == 1:
                    # La celda vecina se convierte en fuego
                    self.grid_details[exp_neighbor] = 2
                    
                    # Agrega la celda vecina como una nueva zona de fantasmas
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
                    break # Detiene la propagación en esa dirección

                # Si la celda vecina ya contiene fuego (2), desencadena otra explosión
                elif self.grid_details.get(exp_neighbor) == 2:
                    self.trigger_explosion(target,exp_neighbor)
                    break

                # Si ninguna condición se cumple, no hace nada (continúa el bucle)
                else:
                    pass
        
        return # Finaliza el manejo de explosiones
    
    # Calcula la dirección de movimiento entre dos posiciones
    def direction(self, start, next):
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

    # Verifica si hay una colisión con un muro o una puerta entre dos posiciones
    def check_collision_walls_doors(self, start, next):
        # Determina la dirección relativa entre las dos posiciones
        direction = self.direction(start, next)
        # Comprueba si hay un muro en la dirección especificada desde la celda inicial
        wall_blocked = direction != None and self.grid_walls[start][0][direction] == '1'
        
        # Verifica si ambas celdas son posiciones de puertas
        if start in self.exit_positions and next in self.exit_positions:
            # Si ambas puertas están abiertas, no hay colisión
            doors_blocked = not (self.exit_positions[start] and self.exit_positions[next])
        
        else:
            # Si no son puertas, se considera bloqueado
            doors_blocked = True
        
        # Devuelve True si hay colisión con un muro o una puerta cerrada
        return wall_blocked and doors_blocked

    # Maneja la expansión de incendios (conversión de humo en fuego)
    # y el daño a los retratos en zonas afectadas por el fuego.
    def process_flashover(self):
        # Procesa la expansión de incendios y fantasmas
        # Expandir incendios: convertir humo en fuego si hay fuego en vecinos
        smoke_cells = [pos for pos, val in self.grid_details.items() if val == 1]
        
        # Expande incendios: convierte humo en fuego si hay fuego en celdas vecinas
        for smoke_cell in smoke_cells:
            # Obtiene los vecinos de la celda con humo
            neighbors = self.grid.get_neighborhood(smoke_cell, moore=False, include_center=False)
            
            for neighbor in neighbors:
                # Si un vecino contiene fuego (valor 2)
                if self.grid_details[neighbor] == 2:  # Si hay fuego en un vecino
                    # Verifica si hay un muro entre las celdas
                    check_wall = self.check_collision_walls(smoke_cell, neighbor)
                    
                    if not check_wall:
                        # Convierte el humo en fuego
                        self.grid_details[smoke_cell] = 2  # Convertir el humo en fuego
                        
                        print(f"[INFO] Humo {smoke_cell} se convierte en fuego.")
                        
                        self.log_event({
                            "type": "smoke_to_fire",
                            "position": smoke_cell,
                            "step": self.step_count
                        })

                        break

        # Procesar puntos con retratos afectados por el fuego
        for point in list(self.portraits):
            # Si hay fuego en una celda con un retrato
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
        
        for cell in self.grid.coord_iter():
            if len(cell[0]) == 0:
                continue

            if self.grid_details[cell[1]] == 2:
                agents = cell[0]
                for agent in agents:
                    agent.reset()

            #agents_in_cell = list(cell_content)  # Agentes en la celda actual
            #print(f"Agentes en la celda ({x}, {y}): {agents_in_cell}")

    # Verifica si hay una colisión entre dos posiciones
    def check_collision_walls(self, start, next):
        # Determina la dirección relativa entre las dos posiciones (0: norte, 1: este, 2: sur, 3: oeste)
        direction = self.direction(start, next)

        # Combina las posiciones 'start' y 'next' para verificar si representan una conexión de salida
        combined_possn = start + next # Ejemplo: (2,3) + (3,3) = (2,3,3,3)
        combined_posns = next + start # Ejemplo: (3,3) + (2,3) = (3,3,2,3)

        # Verifica si la posición 'start' está en el grid_walls
        if start in self.grid_walls:
            # Si está, verifica si hay un muro presente en la dirección calculada
            wall_blocked = direction is not None and self.grid_walls[start][0][direction] == '1'
        else:
            # Si no está en el grid_walls, no hay colisión
            wall_blocked = False  # No hay colisión si la posición no está en el grid

        # Comprueba si la posición combinada está en las salidas
        if (combined_possn in self.exit_positions or 
            combined_posns in self.exit_positions):
            # Si son una salida, no bloquear el paso aunque haya un muro
            wall_blocked = False  # No bloquear si está en una posición de salida
        
        # Devuelve True si hay colisión con un muro, False de lo contrario
        return wall_blocked

    # Actualiza el estado de la simulación
    def update_simulation_status(self):
        # Condición de derrota: número de bajas o daño estructural supera el límite
        if self.casualties >= 4 or self.damage_counter >= 24:
            # Actualiza el estado general a 'Derrota'
            self.simulation_status = "Defeat"
            
            if self.casualties >=4:
                # Establece la razón específica de la derrota
                self.simulation_end = "Defeat by dead victims"
            
            if self.damage_counter >=24:
                # Establece otra posible razón de derrota
                self.simulation_end = "Defeat by damage"
            # Indica que la simulación debe detenerse
            return True
        
        # Condición de victoria: suficientes retratos rescatados
        elif self.rescued >= 7:
            # Cambia el estado general a 'Victoria'
            self.simulation_status = "Victory"
            # Indica que la simulación debe detenerse
            return True
        # Si no se cumple ninguna condición, la simulación continúa
        return False
    
    # Imprime información sobre los agentes registrados en el planificador (Scheduler)
    def print_schedule(self):
        print("Agentes en el Scheduler:")

        # Itera sobre los agentes programados en el Scheduler
        for agent in self.schedule.agents:
            # Muestra el ID, rol y posición de cada agente
            print(f"Agente {agent.unique_id} con rol {agent.role} en posición {agent.pos}")

    # Evoluciona el modelo en un solo turno, incluyendo acciones de agentes y eventos del entorno
    def step(self):
        """Evoluciona un paso del modelo."""
        # Imprime el número de turno actual para seguimiento
        print(f"\n--- Turno {self.step_count} ---")
        # Recolecta datos del modelo y los agentes para análisis futuro
        self.datacollector.collect(self)  # Recolectar datos para análisis

        # Verifica si la simulación debe detenerse debido a condiciones de victoria o derrota
        if self.update_simulation_status():
            print(f"[DEBUG] Estatus de la simulación: {self.simulation_status}")
            # Finaliza el turno si la simulación ha terminado
            return

        # Incrementa el contador de turnos
        self.step_count += 1
        print("[DEBUG] Iniciando pasos de los agentes en orden:")

        # Itera sobre los agentes en el Scheduler, ordenados por su ID único
        for agent in sorted(self.schedule.agents, key=lambda a: a.unique_id):
            # Ejecuta el método `step` de cada agente (su lógica específica de acción)
            agent.step()

            # Procesa la expansión de incendios y otros efectos del entorno
            self.process_flashover()

        # Mostrar la energía restante de todos los agentes al final del turno
        print("\n[DEBUG] Energía de los agentes al final del turno:")
        for agent in sorted(self.schedule.agents, key=lambda a: a.unique_id):
            print(f"  - Agente {agent.unique_id} ({agent.role}): {agent.action_points} de energía.")
        
        # Vuelve a verificar si las condiciones de la simulación han cambiado
        self.update_simulation_status()