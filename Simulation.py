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

    # Inicializar eventos globales
    global_events = set()

    # Simular turnos
    steps = []
    while not model.update_simulation_status():
        turn_data = {"turn": model.step_count, "details": []}
        seen_events = set()  # Para evitar duplicados dentro del turno

        # Procesar turnos de agentes
        for agent in model.schedule.agents:
            agent.step()  # Los eventos se registran dinámicamente aquí

        # Capturar y agregar eventos únicos del turno
        for event in model.model_events:
            event_tuple = tuple(sorted(event.items()))  # Ordenar para evitar duplicados por orden de claves
            if event_tuple not in global_events:
                global_events.add(event_tuple)  # Agregar solo si es nuevo
                if event_tuple not in seen_events:  # Asegurar no repetir dentro del turno
                    seen_events.add(event_tuple)
                    turn_data["details"].append(event)  # Agregar evento único al turno

        # Registrar el turno completo si hay eventos nuevos
        if turn_data["details"]:
            steps.append(turn_data)

        # Ejecutar el paso del modelo
        model.step()

    # Respuesta completa
    response = {
        "agents": agents,
        "steps": steps,
        "unique_events": [dict(e) for e in global_events]  # Convertir a lista de diccionarios
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

