from flask import Flask, jsonify
from collections import OrderedDict
from MansionModel import MansionModel  # Importa tu modelo y agentes
import random

app = Flask(__name__)

SEED = 200
LUIGIS = 6
DEVELOPMENT_MODE = True
FILE_PATH = './final.txt'

def procesar_txt(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Procesar paredes
    WALLS = []
    index = 0
    for _ in range(6):  # 6 líneas de paredes
        row = []
        cells = lines[index].strip().split()
        for cell in cells:
            # Cada celda es un diccionario con paredes explícitas
            walls = {
                "top": int(cell[0]),
                "left": int(cell[1]),
                "bottom": int(cell[2]),
                "right": int(cell[3])
            }
            row.append(walls)
        WALLS.append(row)
        index += 1

    # Procesar puntos de interés
    FAKE_ALARMS = []
    VICTIMS = []
    for _ in range(3):  # Máximo 3 líneas para puntos de interés
        r, c, marker_type = lines[index].strip().split()
        if marker_type == 'f':  # Falsa alarma
            FAKE_ALARMS.append({"row": int(r), "col": int(c)})
        elif marker_type == 'v':  # Víctima
            VICTIMS.append({"row": int(r), "col": int(c)})
        index += 1

    # Procesar marcadores de fuego
    FIRES = []
    for _ in range(10):  # 10 líneas de fuego
        r, c = map(int, lines[index].strip().split())
        FIRES.append({"row": r, "col": c})
        index += 1

    # Procesar marcadores de puertas
    DOORS = []
    for _ in range(8):  # 8 líneas de puertas
        r1, c1, r2, c2 = map(int, lines[index].strip().split())
        DOORS.append({"r1": r1, "c1": c1, "r2": r2, "c2": c2})
        index += 1

    # Procesar puntos de entrada
    ENTRANCES = []
    for _ in range(4):  # 4 líneas de puntos de entrada
        r, c = map(int, lines[index].strip().split())
        ENTRANCES.append({"row": r, "col": c})
        index += 1

    # Usar OrderedDict para asegurar el orden de las claves en el JSON
    data = OrderedDict([
        ("walls", WALLS),
        ("fake_alarms", FAKE_ALARMS),
        ("victims", VICTIMS),
        ("fires", FIRES),
        ("doors", DOORS),
        ("entrances", ENTRANCES),
        ("width", 8),
        ("height", 6)
    ])
    
    return data


def procesar_txt_sim(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Procesar paredes
    WALLS = []
    index = 0
    for _ in range(6):  # 6 líneas de paredes
        row = []
        cells = lines[index].strip().split()
        for cell in cells:
            walls = [int(d) for d in cell]  # Cada celda se descompone en 4 dígitos
            row.append(walls)
        WALLS.append(row)
        index += 1

    # Procesar puntos de interés
    FAKE_ALARMS = []
    VICTIMS = []
    for _ in range(3):  # Máximo 3 líneas para puntos de interés
        r, c, marker_type = lines[index].strip().split()
        if marker_type == 'f':  # Falsa alarma
            FAKE_ALARMS.append((int(r), int(c)))
        elif marker_type == 'v':  # Víctima
            VICTIMS.append((int(r), int(c)))
        index += 1

    # Procesar marcadores de fuego
    FIRES = []
    for _ in range(10):  # 10 líneas de fuego
        r, c = map(int, lines[index].strip().split())
        FIRES.append((r, c))
        index += 1

    # Procesar marcadores de puertas
    DOORS = {}
    DOORS_CONNECTED = {}
    for _ in range(8):  # 8 líneas de puertas
        r1, c1, r2, c2 = map(int, lines[index].strip().split())
        
        # Reorganizar las coordenadas al formato (c1, r1, c2, r2)
        c1, r1, c2, r2 = c1, r1, c2, r2
        
        # Almacenar las puertas con el formato reorganizado
        DOORS[(c1, r1, c2, r2)] = (c1, r1, c2, r2)
        DOORS_CONNECTED[(c1, r1)] = (c2, r2)
        DOORS_CONNECTED[(c2, r2)] = (c1, r1)
        index += 1
        
    # Procesar puntos de entrada
    ENTRANCES = []
    for _ in range(4):  # 4 líneas de puntos de entrada
        r, c = map(int, lines[index].strip().split())
        ENTRANCES.append((r, c))
        index += 1

    return WALLS, FAKE_ALARMS, VICTIMS, FIRES, DOORS, DOORS_CONNECTED, ENTRANCES

@app.route('/get_board', methods=['GET'])
def get_board():
    file_path = './final.txt'  # Ruta del archivo
    data = procesar_txt(file_path)
    return jsonify(data)


@app.route('/run_simulation', methods=['GET'])
def run_simulation():

    # Configurar modelo
    random.seed(SEED)
    WALLS, FAKE_ALARMS, PORTRAITS, GHOSTS, DOORS, DOORS_CONNECTED, ENTRANCES = procesar_txt_sim(FILE_PATH)

    model = MansionModel(LUIGIS, FAKE_ALARMS, 
                         PORTRAITS, WALLS, DOORS, 
                         GHOSTS, ENTRANCES, DEVELOPMENT_MODE, SEED)

    # Registrar agentes iniciales
    agents = [
        {
            "id": agent.unique_id,
            "role": agent.role,
            "initial_position": agent.pos
        }
        for agent in model.schedule.agents
    ]

    # Simular turnos
    steps = []
    while model.step_count <= 1000:
        turn_data = {
            "turn": model.step_count,
            "agent_moves": [],
            "fire_updates": [],
            "portrait_updates": []
        }

        # Procesar movimientos y acciones de agentes
        for agent in model.schedule.agents:
            path = []  # Lista para registrar cada celda recorrida
            actions = []  # Lista para registrar acciones específicas del agente

            # Ejecutar el turno del agente
            agent.step()

            # Registrar cada celda recorrida
            path.extend(agent.history)

            actions.extend(agent.action_history)

            # Verificar si recogió un retrato en la celda actual
            portrait_details = agent.examine_portrait(agent.pos)
            if portrait_details:
                actions.append(f"picked_up_{portrait_details['type']}_at_{portrait_details['position']}")

            # Agregar datos del agente al turno
            agent_data = {
                "id": agent.unique_id,
                "path": path,
                "actions": actions
            }
            turn_data["agent_moves"].append(agent_data)

        # Registrar cambios en fuego
        for position, state in model.grid_details.items():
            if state == 1:
                turn_data["fire_updates"].append({"position": position, "state": "smoke"})
            elif state == 2:
                turn_data["fire_updates"].append({"position": position, "state": "fire"})

        # Registrar cambios en retratos
        for position, portrait_type in model.portraits.items():
            if portrait_type is None:
                turn_data["portrait_updates"].append({"position": position, "state": "removed"})
            elif portrait_type == "victim":
                turn_data["portrait_updates"].append({"position": position, "state": "new_victim"})

        # Agregar datos del turno
        steps.append(turn_data)

        model.step()
        if model.update_simulation_status():
            break

    # Respuesta completa
    response = {
        "agents": agents,
        "steps": steps
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)