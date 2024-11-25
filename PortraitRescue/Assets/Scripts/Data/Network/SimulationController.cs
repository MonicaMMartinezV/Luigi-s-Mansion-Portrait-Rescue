using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using System;

public class SimulationController : MonoBehaviour
{
    public GameObject rescuerPrefab;     // Prefab para rescatistas
    public GameObject firefighterPrefab; // Prefab para bomberos
    public GameObject smokePrefab; // Prefab para el humo

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
                Debug.Log($"Detalles del evento: {JsonConvert.SerializeObject(detail)}");

                if (detail.type == "agent_move")
                {
                    // Procesar el evento 'agent_move' (debe usar ActionData)
                    if (detail.data != null)
                    {
                        // Deserializar 'data' como ActionData
                        ActionData actionData = JsonConvert.DeserializeObject<ActionData>(JsonConvert.SerializeObject(detail.data));
                        Debug.Log($"Procesando agent_move para el agente {actionData.id}");
                        yield return StartCoroutine(MoveAgentAlongPath(actionData));  // Maneja el movimiento del agente
                    }
                    else
                    {
                        Debug.LogWarning("Error: 'data' es nulo para el evento agent_move.");
                    }
                }
                else if (detail.type == "model_event")
                {
                    // Procesar el evento 'model_event' (debe usar ModelEventData)
                    if (detail.data != null)
                    {
                        // Deserializar 'data' como ModelEventData
                        ModelEventData modelEventData = JsonConvert.DeserializeObject<ModelEventData>(JsonConvert.SerializeObject(detail.data));

                        if (modelEventData != null && !string.IsNullOrEmpty(modelEventData.type))
                        {
                            // Verificar si las listas 'position', 'from' y 'to' son nulas antes de usarlas
                            string positionStr = modelEventData.position != null && modelEventData.position.Count > 0
                                ? string.Join(", ", modelEventData.position)
                                : "N/A";  // Valor alternativo si la lista está vacía o es nula

                            string fromStr = modelEventData.from != null && modelEventData.from.Count > 0
                                ? string.Join(", ", modelEventData.from)
                                : "N/A";  // Valor alternativo si la lista está vacía o es nula

                            string toStr = modelEventData.to != null && modelEventData.to.Count > 0
                                ? string.Join(", ", modelEventData.to)
                                : "N/A";  // Valor alternativo si la lista está vacía o es nula

                            Debug.Log($"Evento model_event deserializado: Tipo: {modelEventData.type}, Posición: [{positionStr}], From: [{fromStr}], To: [{toStr}], Paso: {modelEventData.step}");
                            HandleModelEvent(modelEventData);  // Maneja el evento model_event
                        }
                        else
                        {
                            Debug.LogWarning("El campo 'type' de model_event no está presente o 'modelEventData' es nulo.");
                        }
                    }
                    else
                    {
                        Debug.LogWarning("Error: 'data' es nulo para el evento model_event.");
                    }
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
                    else if (action.Contains("Fire extinguished at"))
                    {
                        HandleFireExtinguished(action);
                    }
                    else if (action.Contains("Fire reduced to smoke at"))
                    {
                        HandleFireReducedToSmoke(action);
                    }
                    yield return new WaitForSeconds(1f);
                }
            }
        }

        agentPositions[move.id] = currentPosition;
    }

    void HandleModelEvent(ModelEventData eventData)
    {
        switch (eventData.type)
        {
            case "smoke_added":
                HandleSmokeAdded(eventData.position);
                break;
            case "damage_registered":
                HandleDamageRegistered(eventData.position);
                break;
            case "fire_extended":
                HandleFireExtended(eventData.from, eventData.to);
                break;
            case "wall_destroyed":
                HandleWallDestroyed(eventData.from, eventData.to);
                break;
            default:
                Debug.LogWarning($"Evento no manejado: {eventData.type}");
                break;
        }
    }

    void HandleSmokeAdded(List<int> position)
    {
        Debug.Log($"Humo añadido en posición ({position[0]}, {position[1]})");
        InstantiateSmokePrefab(position[0], position[1]);
    }

    void HandleDamageRegistered(List<int> position)
    {
        Debug.Log($"Daño registrado en posición ({position[0]}, {position[1]})");
        // Lógica para mostrar daño visual o cambiar estado del suelo
    }

    void HandleFireExtended(List<int> from, List<int> to)
    {
        Debug.Log($"Fuego extendido de ({from[0]}, {from[1]}) a ({to[0]}, {to[1]})");
        // Lógica para manejar la extensión del fuego
    }

    void HandleWallDestroyed(List<int> from, List<int> to)
    {
        Debug.Log($"Muro destruido de ({from[0]}, {from[1]}) a ({to[0]}, {to[1]})");
        // Lógica para eliminar un muro en el juego
    }

    void HandleFireReducedToSmoke(string action)
    {
        var match = System.Text.RegularExpressions.Regex.Match(action, @"Fire reduced to smoke at: \((\d+), (\d+)\)");
        if (match.Success)
        {
            int x = int.Parse(match.Groups[1].Value);
            int y = int.Parse(match.Groups[2].Value);

            GameObject ghost = GameObject.Find($"Ghost ({x},{y})");
            if (ghost != null)
            {
                Debug.Log($"Fuego reducido a humo en ({x}, {y}). Animando ghost y reemplazando con humo.");
                StartCoroutine(AnimateGhostToSmoke(ghost, x, y));
            }
            else
            {
                Debug.LogWarning($"No se encontró el ghost en las coordenadas ({x}, {y}).");
            }
        }
    }

    IEnumerator AnimateGhostToSmoke(GameObject ghost, int x, int y)
    {
        float duration = 2f; // Duración de cada animación
        float timeElapsed = 0f;

        Vector3 initialScale = ghost.transform.localScale;
        Quaternion initialRotation = ghost.transform.rotation;

        // Animación para hacer desaparecer el ghost
        while (timeElapsed < duration)
        {
            float t = timeElapsed / duration;
            ghost.transform.localScale = Vector3.Lerp(initialScale, Vector3.zero, t); // Reducir tamaño
            ghost.transform.rotation = Quaternion.Euler(0f, 360f * t, 0f); // Hacerlo girar
            timeElapsed += Time.deltaTime;
            yield return null;
        }

        Destroy(ghost); // Destruir el ghost después de la animación

        // Crear el nuevo prefab (humo) en su lugar
        GameObject smoke = InstantiateSmokePrefab(x, y);

        // Animación para que el prefab aparezca creciendo y girando
        timeElapsed = 0f;
        Vector3 finalScale = smoke.transform.localScale;
        smoke.transform.localScale = Vector3.zero; // Comenzar desde escala cero

        while (timeElapsed < duration)
        {
            float t = timeElapsed / duration;
            smoke.transform.localScale = Vector3.Lerp(Vector3.zero, finalScale, t); // Incrementar tamaño
            smoke.transform.rotation = Quaternion.Euler(0f, 360f * t, 0f); // Hacerlo girar
            timeElapsed += Time.deltaTime;
            yield return null;
        }
    }

    GameObject InstantiateSmokePrefab(int x, int y)
    {
        GameObject floor = GameObject.Find($"Floor ({x},{y})");
        if (floor != null)
        {
            Vector3 position = floor.transform.position + new Vector3(0, 1f, 0); // Posición encima del suelo
            GameObject smoke = Instantiate(smokePrefab, position, Quaternion.identity);
            smoke.name = $"Smoke ({x},{y})"; // Asignar un nombre al prefab
            return smoke;
        }
        else
        {
            Debug.LogWarning($"No se encontró el suelo en ({x},{y}) para colocar el humo.");
            return null;
        }
    }

    void HandleFireExtinguished(string action)
    {
        var match = System.Text.RegularExpressions.Regex.Match(action, @"Fire extinguished at: \((\d+), (\d+)\)");
        if (match.Success)
        {
            int x = int.Parse(match.Groups[1].Value);
            int y = int.Parse(match.Groups[2].Value);

            GameObject ghost = GameObject.Find($"Ghost ({x},{y})");
            if (ghost != null)
            {
                Debug.Log($"Fuego extinguido en ({x}, {y}). Comenzando animación de ghost.");
                StartCoroutine(AnimateGhost(ghost));
            }
            else
            {
                Debug.LogWarning($"No se encontró el ghost en las coordenadas ({x}, {y}).");
            }
        }
    }

    IEnumerator AnimateGhost(GameObject ghost)
    {
        float duration = 2f; // Duración de la animación
        float timeElapsed = 0f;
        Vector3 initialScale = ghost.transform.localScale;
        Quaternion initialRotation = ghost.transform.rotation;

        // Hacer que el ghost gire y se reduzca de tamaño
        while (timeElapsed < duration)
        {
            float t = timeElapsed / duration;
            ghost.transform.localScale = Vector3.Lerp(initialScale, Vector3.zero, t); // Reducir tamaño
            ghost.transform.rotation = Quaternion.Euler(0f, 360f * t, 0f); // Hacerlo girar
            timeElapsed += Time.deltaTime;
            yield return null;
        }

        // Destruir el ghost después de la animación
        Destroy(ghost);
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
                                Material randomMaterial = victimMaterials[UnityEngine.Random.Range(0, victimMaterials.Length)];
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
    public string type;                // Tipo de evento: "agent_move" o "model_event"
    public object data;                // Usamos 'object' para que pueda ser ActionData o ModelEventData
    public ModelEventData model_event_data;  // Esto es para acceder directamente a model_event_data si está presente
}

[System.Serializable]
public class ActionData
{
    public List<string> actions;       // Acciones realizadas por el agente
    public int id;                     // ID del agente
    public List<List<int>> path;       // Ruta del agente, representada como listas de coordenadas [x, y]
}

[System.Serializable]
public class ModelEventData
{
    public List<int> position;         // Posición del evento en formato [x, y]
    public List<int> from;             // Para eventos de tipo "fire_extended"
    public List<int> to;               // Para eventos de tipo "fire_extended"
    public string type;                // Tipo de evento: "smoke_added", "fire_extinguished", etc.
    public int step;                   // Paso del evento
}

