using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class SimulationController : MonoBehaviour
{
    public GameObject rescuerPrefab;     // Prefab para rescatistas
    public GameObject firefighterPrefab; // Prefab para bomberos
    public float moveSpeed = 100f;
    private Dictionary<int, GameObject> agents = new Dictionary<int, GameObject>();
    private Dictionary<int, Vector3> agentPositions = new Dictionary<int, Vector3>(); // Para almacenar las posiciones de los agentes

    [Header("API Config")]
    public string simulationApiUrl = "http://127.0.0.1:5000/run_simulation"; // Cambia la URL a tu servidor

    private SimulationData simulationData;

    void Start()
    {
        StartCoroutine(LoadSimulationData());
    }

    IEnumerator LoadSimulationData()
    {
        using (UnityWebRequest request = UnityWebRequest.Get(simulationApiUrl))
        {
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                string json = request.downloadHandler.text;
                Debug.Log("Datos recibidos: " + json);

                simulationData = JsonConvert.DeserializeObject<SimulationData>(json);

                if (simulationData != null)
                {
                    InitializeAgents();
                    StartCoroutine(RunSimulation());
                }
                else
                {
                    Debug.LogError("Error al deserializar los datos de la simulación.");
                }
            }
            else
            {
                Debug.LogError("Error al conectar con la API: " + request.error);
            }
        }
    }

    void InitializeAgents()
    {
        foreach (var agentData in simulationData.agents)
        {
            Vector3 initialPosition = GetFloorPosition(agentData.initial_position[0], agentData.initial_position[1]);
            GameObject prefab = agentData.role == "rescuer" ? rescuerPrefab : firefighterPrefab;
            GameObject agent = Instantiate(prefab, initialPosition, Quaternion.identity);
            agent.name = $"Agent_{agentData.id}";
            agents[agentData.id] = agent;
            agentPositions[agentData.id] = initialPosition; // Guardar la posición inicial
        }
    }

    IEnumerator RunSimulation()
    {
        foreach (var step in simulationData.steps)
        {
            Debug.Log($"Turno: {step.turn}");

            // Inicia el movimiento de cada agente en secuencia (uno por uno)
            foreach (var move in step.agent_moves)
            {
                yield return StartCoroutine(MoveAgentAlongPath(move));
            }

            // Breve pausa al final del paso para visualización
            yield return new WaitForSeconds(1f);
        }
    }

    IEnumerator MoveAgentAlongPath(AgentMove move)
    {
        GameObject agent = agents[move.id];

        // Obtener la posición actual del agente
        Vector3 currentPosition = agentPositions[move.id];

        // Encontrar el índice en el path desde donde el agente debe continuar
        int startIndex = FindClosestPathIndex(move.path, currentPosition);

        // Recorre el path desde el índice encontrado
        for (int i = startIndex; i < move.path.Count; i++)
        {
            Vector3 targetPosition = GetFloorPosition(move.path[i][0], move.path[i][1]);

            // Mueve al agente hacia la siguiente posición en el camino
            while (Vector3.Distance(currentPosition, targetPosition) > 0.01f)
            {
                agent.transform.position = Vector3.MoveTowards(agent.transform.position, targetPosition, Time.deltaTime * moveSpeed);
                currentPosition = agent.transform.position;
                yield return null;
            }

            // Si hay acciones asociadas a esta posición, ejecútalas
            foreach (var action in move.actions)
            {
                if (IsActionAtPosition(move.path[i], action))
                {
                    Debug.Log($"Agente {move.id} realizando acción: {action}");
                    yield return new WaitForSeconds(1f); // Pausa breve para visualizar la acción
                }
            }
        }

        // Actualiza la última posición del agente al final del movimiento
        agentPositions[move.id] = currentPosition;
    }

    // Encuentra el índice más cercano en el path a la posición actual
    int FindClosestPathIndex(List<List<int>> path, Vector3 currentPosition)
    {
        float minDistance = float.MaxValue;
        int closestIndex = 0;

        for (int i = 0; i < path.Count; i++)
        {
            Vector3 pathPosition = GetFloorPosition(path[i][0], path[i][1]);
            float distance = Vector3.Distance(currentPosition, pathPosition);

            if (distance < minDistance)
            {
                minDistance = distance;
                closestIndex = i;
            }
        }

        return closestIndex;
    }



    // Función para encontrar la posición del 'Floor' en base a coordenadas
    Vector3 GetFloorPosition(int x, int y)
    {
        GameObject floor = GameObject.Find($"Floor ({x},{y})");
        if (floor != null)
        {
            return floor.transform.position + new Vector3(0, 1f, 0);  // Desplaza el agente justo encima del piso
        }
        else
        {
            Debug.LogWarning($"Floor ({x},{y}) no encontrado.");
            return Vector3.zero;
        }
    }

    // Función para comprobar si la acción está en la posición actual
    bool IsActionAtPosition(List<int> position, string action)
    {
        string posString = $"({position[0]}, {position[1]})";
        return action.Contains(posString);
    }
}

// Clases para deserializar el JSON
[System.Serializable]
public class SimulationData
{
    public List<Agent> agents;
    public List<Step> steps;
}

[System.Serializable]
public class Agent
{
    public int id;
    public List<int> initial_position;
    public string role;
}

[System.Serializable]
public class Step
{
    public int turn;
    public List<AgentMove> agent_moves;
}

[System.Serializable]
public class AgentMove
{
    public int id;
    public List<List<int>> path;
    public List<string> actions;
}
