from flask import Flask, jsonify
from collections import OrderedDict
from MansionModel import MansionModel  # Importa tu modelo y agentes
import random

# Librerías de manipulación y análisis de datos
import numpy as np  # Proporciona funciones para manejo de matrices y álgebra lineal, común en análisis de datos
import pandas as pd  # Ofrece estructuras de datos como DataFrames, útiles para manipular grandes cantidades de datos
import time  # Proporciona funciones para trabajar con fechas y horas

app = Flask(__name__)

SEED = 31
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
    # Número de simulaciones a ejecutar
    NUM_SIMULACIONES = 1
    count_victory = 0

    # Almacenar resultados
    resultados_simulaciones = []

    for sim in range(NUM_SIMULACIONES):
        # Configurar la semilla
        if DEVELOPMENT_MODE:
            SEED = 31
        else:
            SEED = int(time.time()) + sim
        
        random.seed(SEED)
        np.random.seed(SEED)

        # Procesar el archivo y configurar el modelo
        WALLS, FAKE_ALARMS, VICTIMS, FIRES, DOORS, DOORS_CONNECTED, ENTRANCES = procesar_txt_sim(FILE_PATH)
        model = MansionModel(
            LUIGIS, FAKE_ALARMS, 
            VICTIMS, WALLS, DOORS, 
            FIRES, ENTRANCES, DEVELOPMENT_MODE, SEED
        )

        # Registrar agentes iniciales
        agents = [
            {
                "id": agent.unique_id,
                "role": agent.role,
                "initial_position": agent.pos
            }
            for agent in model.schedule.agents
        ]

        # Simulación paso a paso
        while model.step_count <= 1000:
            model.step()

            # Verificar el estado de la simulación
            if model.update_simulation_status():
                break

        # Registrar resultados
        response = {
            "agents": agents,
            "steps": model.model_events  # Enviar eventos en orden registrado
        }

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

