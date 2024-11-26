from MansionModel import MansionModel
from LuigiAgentTest import LuigiAgent

# Librerías de visualización y gráficos
import matplotlib.pyplot as plt  # Creación y personalización de gráficos
import matplotlib.patches as patches  # Añade formas como rectángulos o círculos a gráficos de matplotlib
from matplotlib.colors import ListedColormap  # Define mapas de color personalizados
import matplotlib.animation as animation  # Crea animaciones, útil para representar dinámicamente la simulación
plt.rcParams["animation.html"] = "jshtml"  # Configura la visualización de animaciones en formato HTML
import matplotlib  # Configuración adicional de matplotlib
matplotlib.rcParams["animation.embed_limit"] = 2**128  # Ajusta el límite de tamaño para incrustar animaciones

# Librerías de manipulación y análisis de datos
import numpy as np  # Proporciona funciones para manejo de matrices y álgebra lineal, común en análisis de datos
import pandas as pd  # Ofrece estructuras de datos como DataFrames, útiles para manipular grandes cantidades de datos
import time  # Proporciona funciones para trabajar con fechas y horas

# Librerías de comunicación en red y servidor HTTP
from http.server import BaseHTTPRequestHandler, HTTPServer  # Implementa un servidor HTTP básico para manejar solicitudes
import logging  # Registro de eventos y errores del servidor, útil para el diagnóstico
import json  # Proporciona funciones para manejar datos en formato JSON, útil para comunicación entre aplicaciones

import heapq
from queue import Queue

DEVELOPMENT_MODE = False
WAIT_TIME = 0.01
SEED = 14

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

# Ruta del archivo
file_path = './final.txt'

# Llamar a la función
WALLS, FAKE_ALARMS, VICTIMS, FIRES, DOORS, DOORS_CONNECTED, ENTRANCES = procesar_txt(file_path)

# Imprimir los resultados
print("Paredes:")
for row in WALLS:
    print(row)

print("\nFalsas alarmas:", FAKE_ALARMS)
print("\nVíctimas:", VICTIMS)
print("\nFuegos:", FIRES)
print("\nPuertas:", DOORS)
print("\nPuertas conectadas:", DOORS_CONNECTED)
print("\nEntradas:", ENTRANCES)

# PARÁMETROS
WIDTH = 9
HEIGHT = 7
LUIGIS = 6

WALLS, FAKE_ALARMS, PORTRAITS, GHOSTS, DOORS, DOORS_CONNECTED, ENTRANCES = procesar_txt(file_path)

# Definir el número de simulaciones que quieres ejecutar
NUM_SIMULACIONES = 1

# Para almacenar los resultados de cada simulación
resultados_simulaciones = []

for sim in range(NUM_SIMULACIONES):
    print(f"\n--- Simulación {sim + 1} ---")
    model = MansionModel(LUIGIS, FAKE_ALARMS, 
                         PORTRAITS, WALLS, DOORS, 
                         GHOSTS, ENTRANCES, DEVELOPMENT_MODE, SEED)
    time.sleep(WAIT_TIME) if DEVELOPMENT_MODE else None
    
    steps = 0
    while model.step_count <= 1:
        model.step()
        steps += 1

        # Verificar si la simulación ha terminado
        if model.update_simulation_status():
            print(f"[DEBUG] Condición de fin alcanzada: {model.simulation_status}")
            break

        # Mostrar la energía de cada Luigi al final de cada turno
        print(f"Turno {steps}: Energía de los luigis:")
        for agent in model.schedule.agents:
            if isinstance(agent, LuigiAgent):
                print(f"{agent.unique_id}: {agent.action_points} de energía")

    # Al finalizar, mostrar el estado final
    print(f"[DEBUG] La simulación ha terminado. Estatus: {model.simulation_status}")

    # Guardar resultados de la simulación actual
    resultado = {
        "simulacion": sim + 1,
        "steps": steps,
        # Changed the attributes to match the MansionModel class definition
        "damage": model.damage_counter,
        "total_deaths": model.losses,
        "saved_victims": model.rescued
    }
    resultados_simulaciones.append(resultado)

    # Mostrar los resultados de la simulación actual
    print(f"Simulación {sim + 1} Finalizada:")
    print(f"Number of steps: {steps}")
    # Changed the attributes to match the MansionModel class definition
    print(f"Damage: {model.damage_counter}")
    print(f"Deaths: {model.losses}")
    print(f"Saved Victims: {model.rescued}")
    if model.damage_counter >= 24:
        print("MANSION TAKEN OVER")
        print("GAME OVER")
    elif model.losses >= 4:
        print("4 DEATHS")
        print("GAME OVER")
    elif model.rescued >= 7:
        print("VICTORY!!!!")

# Mostrar un resumen de los resultados de todas las simulaciones
print("\n--- Resumen de todas las simulaciones ---")
for resultado in resultados_simulaciones:
    print(f"Simulación {resultado['simulacion']}:")
    print(f"  Steps: {resultado['steps']}")
    print(f"  Damage: {resultado['damage']}")
    print(f"  Deaths: {resultado['total_deaths']}")
    print(f"  Saved Victims: {resultado['saved_victims']}")