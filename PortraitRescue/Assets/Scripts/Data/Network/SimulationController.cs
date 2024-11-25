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

    [Header("Portrait Settings")]
    public Material falseMaterial;
    public Material[] victimMaterials;

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

            foreach (var detail in step.details)
            {
                if (detail.type == "agent_move")
                {
                    yield return StartCoroutine(MoveAgentAlongPath(detail.data));
                }
            }

            yield return new WaitForSeconds(1f);
        }
    }

    IEnumerator MoveAgentAlongPath(ActionData move)
    {
        if (!agents.ContainsKey(move.id))
        {
            Debug.LogError($"Agente con ID {move.id} no encontrado.");
            yield break;
        }

        GameObject agent = agents[move.id];
        Vector3 currentPosition = agentPositions[move.id];
        int startIndex = FindClosestPathIndex(move.path, currentPosition);

        for (int i = startIndex; i < move.path.Count; i++)
        {
            Vector3 targetPosition = GetFloorPosition(move.path[i][0], move.path[i][1]);

            while (Vector3.Distance(currentPosition, targetPosition) > 0.01f)
            {
                agent.transform.position = Vector3.MoveTowards(agent.transform.position, targetPosition, Time.deltaTime * moveSpeed);
                currentPosition = agent.transform.position;
                yield return null;
            }

            foreach (var action in move.actions)
            {
                if (IsActionAtPosition(move.path[i], action))
                {
                    Debug.Log($"Agente {move.id} realizando acción: {action}");
                    if (action.Contains("Portrait found"))
                    {
                        HandlePortraitFound(action, agent);
                    }
                    else if (action.Contains("Portrait rescued"))
                    {
                        HandlePortraitRescued(agent);
                    }

                    yield return new WaitForSeconds(1f);
                }
            }
        }

        agentPositions[move.id] = currentPosition;
    }

    void HandlePortraitFound(string action, GameObject agent)
    {
        var match = System.Text.RegularExpressions.Regex.Match(action, @"Portrait found at: \((\d+), (\d+)\), Type: (\w+)");
        if (match.Success)
        {
            int x = int.Parse(match.Groups[1].Value);
            int y = int.Parse(match.Groups[2].Value);
            string type = match.Groups[3].Value;

            GameObject mainPortrait = GameObject.Find($"Portrait ({x},{y})");
            if (mainPortrait != null)
            {
                Transform innerPortrait = mainPortrait.transform.Find("Portrait");
                if (innerPortrait != null)
                {
                    Transform mesh4 = innerPortrait.Find("Mesh4");
                    if (mesh4 != null)
                    {
                        Renderer renderer = mesh4.GetComponent<Renderer>();
                        if (renderer != null)
                        {
                            if (type == "Victim")
                            {
                                // Cambiar material y convertir en hijo del agente
                                Material randomMaterial = victimMaterials[Random.Range(0, victimMaterials.Length)];
                                renderer.material = randomMaterial;
                                Debug.Log($"Retrato en ({x}, {y}) identificado como 'Victim'. Ahora es hijo de {agent.name}.");
                                LevitateAndRotate levitateAndRotate = mainPortrait.GetComponent<LevitateAndRotate>();
                                if (levitateAndRotate != null)
                                {
                                    Destroy(levitateAndRotate); // Eliminar el componente
                                    Debug.Log("Componente LevitateAndRotate eliminado del retrato.");
                                }
                                else
                                {
                                    Debug.LogWarning("El retrato no tiene el componente LevitateAndRotate.");
                                }
                                mainPortrait.transform.SetParent(agent.transform);
                            }
                            else if (type == "False")
                            {
                                // Cambiar material y destruir después de 2 segundos
                                renderer.material = falseMaterial;
                                Debug.Log($"Retrato en ({x}, {y}) identificado como 'False'. Destruyendo retrato.");
                                Destroy(mainPortrait, 2f);
                            }
                        }
                    }
                }
            }
        }
    }

    void HandlePortraitRescued(GameObject agent)
    {
        Transform portrait = null;

        foreach (Transform child in agent.transform.GetComponentsInChildren<Transform>())
        {
            if (child.name.Contains("Portrait"))
            {
                portrait = child;
                break; // Salir del bucle tras encontrarlo
            }
        }

        if (portrait != null)
        {
            Debug.Log($"Retrato rescatado por {agent.name}. Destruyendo retrato: {portrait.name}");
            Destroy(portrait.gameObject);
        }
        else
        {
            Debug.LogWarning($"El agente {agent.name} no tiene un retrato para rescatar.");
        }
    }

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

    Vector3 GetFloorPosition(int x, int y)
    {
        GameObject floor = GameObject.Find($"Floor ({x},{y})");
        if (floor != null)
        {
            return floor.transform.position + new Vector3(0, 1f, 0);
        }
        else
        {
            Debug.LogWarning($"Floor ({x},{y}) no encontrado.");
            return Vector3.zero;
        }
    }

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
    public List<Detail> details;
}

[System.Serializable]
public class Detail
{
    public string type;
    public ActionData data;
}

[System.Serializable]
public class ActionData
{
    public List<string> actions;
    public int id;
    public List<List<int>> path;
}

