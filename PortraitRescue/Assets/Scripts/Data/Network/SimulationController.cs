using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using System.IO;

public class SimulationController : MonoBehaviour
{
    public GameObject rescuerPrefab;
    public GameObject firefighterPrefab;
    public GameObject smokePrefab;
    public GameObject ghostPrefab;
    public GameObject portraitPrefab;
    public Material falseMaterial;
    public Material[] victimMaterials;

    public float moveSpeed = 5f;

    private Dictionary<int, GameObject> agents = new Dictionary<int, GameObject>();
    private Dictionary<int, Vector3> agentPositions = new Dictionary<int, Vector3>();

    public string simulationApiUrl = "http://127.0.0.1:5000/run_simulation";

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
        foreach (var agent in simulationData.agents)
        {
            Vector3 initialPosition = GetFloorPosition(agent.initial_position[0], agent.initial_position[1]);
            GameObject prefab = agent.role == "rescuer" ? rescuerPrefab : firefighterPrefab;
            GameObject agentObj = Instantiate(prefab, initialPosition, Quaternion.identity);
            agentObj.name = $"Agent_{agent.id}";
            agents[agent.id] = agentObj;
            agentPositions[agent.id] = initialPosition;
        }
    }

    IEnumerator RunSimulation()
    {
        int totalDetailsProcessed = 0;

        foreach (var step in simulationData.steps)
        {
            Debug.Log($"Turno: {step.turn}, Total de detalles: {step.details.Count}");

            foreach (var detail in step.details)
            {
                totalDetailsProcessed++;
                Debug.Log($"Procesando detalle #{totalDetailsProcessed}: {detail.type}");

                HandleDetail(detail);
                yield return new WaitForSeconds(1f);
            }
        }

        Debug.Log($"Simulación completada. Total de detalles procesados: {totalDetailsProcessed}");
    }



    void HandleDetail(Detail detail)
    {
        Debug.Log($"Detalle actual: Tipo = {detail.type}");

        switch (detail.type)
        {
            case "agent_move":
                HandleAgentMove(detail);
                break;
            case "smoke_added":
                HandleSmokeAdded(detail.position);
                break;
            case "found_portrait":
                HandlePortraitFound(detail);
                break;
            case "fire_extinguished":
                HandleFireExtinguished(detail.position);
                break;
            case "portrait_added":
                HandlePortraitAdded(detail.position);
                break;
            case "fire_removed_to_portrait":
                HandleFireExtinguished(detail.position);
                break;
            case "rescued_portrait":
                HandlePortraitRescued(detail);
                break;
            case "wall_destroyed":
                Debug.Log($"Detalles recibidos para WallDestroyed - Position: {string.Join(", ", detail.position ?? new List<int>())}, Target: {string.Join(", ", detail.target ?? new List<int>())}");
                HandleWallDestroyed(detail.position,detail.target);
                break;
            case "fire_to_smoke":
                HandleFireExtinguished(detail.position);
                HandleSmokeAdded(detail.position);
                break;
            case "smoke_extinguished":
                HandleSmokeExtinguished(detail.position);
                break;
            case "smoke_to_fire":
                HandleSmokeExtinguished(detail.position);
                HandleFireAdded(detail.position);
                break;
            case 
            default:
                Debug.LogWarning($"Evento no manejado: {detail.type}");
                break;
        }
    }


    IEnumerator MoveAgent(GameObject agent, Vector3 fromPosition, Vector3 toPosition)
    {
        // Tiempo de duración del movimiento
        float timeElapsed = 0f;
        float moveDuration = 1f; // Puedes ajustar este valor para hacer el movimiento más rápido o lento

        while (timeElapsed < moveDuration)
        {
            // Interpolación del movimiento
            agent.transform.position = Vector3.Lerp(fromPosition, toPosition, timeElapsed / moveDuration);
            timeElapsed += Time.deltaTime; // Incrementar el tiempo
            yield return null; // Esperar el siguiente frame
        }

        // Asegurarse de que el agente termine en la posición final
        agent.transform.position = toPosition;
    }

    IEnumerator AnimateReduce(GameObject ghost)
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

    void HandleWallDestroyed(List<int> position, List<int> target)
    {
        if (position == null || position.Count < 2)
        {
            Debug.LogError("Position inválida o nula en HandleWallDestroyed.");
            return;
        }

        if (target == null || target.Count < 2)
        {
            Debug.LogError("Target inválido o nulo en HandleWallDestroyed.");
            return;
        }

        int xPos = position[0];
        int yPos = position[1];
        int xTarget = target[0];
        int yTarget = target[1];

        string wallTypeFromPosition = "";
        string wallTypeFromTarget = "";

        // Determinar el tipo de pared en `position`
        if (xPos == xTarget)  // Mismo X (Vertical)
        {
            if (yTarget < yPos)
            {
                wallTypeFromPosition = "UpperWall";
                wallTypeFromTarget = "BottomWall";
            }
            else if (yTarget > yPos)
            {
                wallTypeFromPosition = "BottomWall";
                wallTypeFromTarget = "UpperWall";
            }
        }
        else if (yPos == yTarget)  // Mismo Y (Horizontal)
        {
            if (xTarget > xPos)
            {
                wallTypeFromPosition = "RightWall";
                wallTypeFromTarget = "LeftWall";
            }
            else if (xTarget < xPos)
            {
                wallTypeFromPosition = "LeftWall";
                wallTypeFromTarget = "RightWall";
            }
        }

        Debug.Log($"Posición: ({xPos},{yPos}), Target: ({xTarget},{yTarget}), WallTypeFromPosition: {wallTypeFromPosition}, WallTypeFromTarget: {wallTypeFromTarget}");

        // Destruir la pared en `position`
        GameObject floorPosition = GameObject.Find($"Floor ({xPos},{yPos})");
        if (floorPosition != null)
        {
            Transform wallTransform = floorPosition.transform.Find(wallTypeFromPosition);
            if (wallTransform != null)
            {
                Debug.Log($"Destruyendo {wallTypeFromPosition} en Floor ({xPos},{yPos})");
                Destroy(wallTransform.gameObject);
            }
            else
            {
                Debug.LogWarning($"No se encontró el {wallTypeFromPosition} dentro de Floor ({xPos},{yPos}).");
            }
        }
        else
        {
            Debug.LogWarning($"No se encontró Floor en la posición ({xPos},{yPos}).");
        }

        // Destruir la pared en `target`
        GameObject floorTarget = GameObject.Find($"Floor ({xTarget},{yTarget})");
        if (floorTarget != null)
        {
            Transform wallTransform = floorTarget.transform.Find(wallTypeFromTarget);
            if (wallTransform != null)
            {
                Debug.Log($"Destruyendo {wallTypeFromTarget} en Floor ({xTarget},{yTarget})");
                Destroy(wallTransform.gameObject);
            }
            else
            {
                Debug.LogWarning($"No se encontró el {wallTypeFromTarget} dentro de Floor ({xTarget},{yTarget}).");
            }
        }
        else
        {
            Debug.LogWarning($"No se encontró Floor en la posición ({xTarget},{yTarget}).");
        }
    }

    void HandleAgentMove(Detail detail)
    {
        // Formar el nombre del agente usando el 'id' del agente
        string agentName = $"Agent_{detail.agent}";

        // Buscar el agente en la escena por su nombre
        GameObject agent = GameObject.Find(agentName);

        if (agent == null)
        {
            Debug.LogWarning($"Agente con nombre {agentName} no encontrado.");
            return;
        }

        // Obtener las coordenadas de 'from' y 'to'
        Vector3 fromPosition = GetFloorPosition(detail.from[0], detail.from[1]);
        Vector3 toPosition = GetFloorPosition(detail.to[0], detail.to[1]);

        // Mover el agente de 'from' a 'to'
        StartCoroutine(MoveAgent(agent, fromPosition, toPosition));
    }

    IEnumerator AnimateSmokeAppearance(GameObject smoke, float duration)
    {
        float elapsedTime = 0f;
        
        // Tamaño y rotación inicial
        Vector3 initialScale = Vector3.zero; // Comienza desde escala cero
        Vector3 finalScale = Vector3.one* 14.72102f;    // Tamaño final normal
        Quaternion initialRotation = Quaternion.Euler(0, 0, 0); // Rotación inicial
        Quaternion finalRotation = smoke.transform.rotation;    // Rotación final deseada
        
        // Aplicar el tamaño inicial
        smoke.transform.localScale = initialScale;
        smoke.transform.rotation = initialRotation;

        // Animar la escala y rotación
        while (elapsedTime < duration)
        {
            elapsedTime += Time.deltaTime;
            float t = Mathf.Clamp01(elapsedTime / duration);

            // Interpolación para la escala y la rotación
            smoke.transform.localScale = Vector3.Lerp(initialScale, finalScale, t);
            smoke.transform.rotation = Quaternion.Lerp(initialRotation, finalRotation, t);

            yield return null; // Esperar el siguiente frame
        }

        // Asegurar el tamaño y rotación finales
        smoke.transform.localScale = finalScale;
        smoke.transform.rotation = finalRotation;
    }

    IEnumerator AnimateGhostAppearance(GameObject ghost, float duration)
    {
        float elapsedTime = 0f;
        
        // Tamaño y rotación inicial
        Vector3 initialScale = Vector3.zero; // Comienza desde escala cero
        Vector3 finalScale = Vector3.one* 4.887948f;    // Tamaño final normal
        Quaternion initialRotation = Quaternion.Euler(0, 0, 0); // Rotación inicial
        Quaternion finalRotation = ghost.transform.rotation;    // Rotación final deseada
        
        // Aplicar el tamaño inicial
        ghost.transform.localScale = initialScale;
        ghost.transform.rotation = initialRotation;

        // Animar la escala y rotación
        while (elapsedTime < duration)
        {
            elapsedTime += Time.deltaTime;
            float t = Mathf.Clamp01(elapsedTime / duration);

            // Interpolación para la escala y la rotación
            ghost.transform.localScale = Vector3.Lerp(initialScale, finalScale, t);
            ghost.transform.rotation = Quaternion.Lerp(initialRotation, finalRotation, t);

            yield return null; // Esperar el siguiente frame
        }

        // Asegurar el tamaño y rotación finales
        ghost.transform.localScale = finalScale;
        ghost.transform.rotation = finalRotation;
    }


    void HandleSmokeAdded(List<int> position)
    {
        // Verificar que la posición sea válida
        if (position == null || position.Count < 2)
        {
            Debug.LogWarning("Posición inválida para agregar humo.");
            return;
        }

        int x = position[0];
        int y = position[1];

        GameObject cell = GameObject.Find($"Floor ({x},{y})");

        if (cell != null)
        {
            Debug.Log($"Instanciando humo en la celda: ({x}, {y})");

            // Obtener la posición de la celda
            Vector3 cellPosition = cell.transform.position;

            // Crear la nueva posición ajustada
            float offsetX = 8.89999962f - 45.9133606f;
            float offsetY = 1.05304384f - 0f;
            float offsetZ = 176.300003f - 139.199997f;
            Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y + offsetY, cellPosition.z + offsetZ);

            // Instanciar el prefab del humo
            GameObject smoke = Instantiate(smokePrefab, adjustedPosition, Quaternion.Euler(0, -230f, 0));

            // Iniciar la corutina para animar el humo
            StartCoroutine(AnimateSmokeAppearance(smoke, 2f)); // 2 segundos de duración

            smoke.name = $"Smoke ({x},{y})";
        }
        else
        {
            Debug.LogWarning($"No se encontró la celda en: ({x}, {y})");
        }
    }

    void HandleFireAdded(List<int> position)
    {
        // Verificar que la posición sea válida
        if (position == null || position.Count < 2)
        {
            Debug.LogWarning("Posición inválida para agregar humo.");
            return;
        }

        int x = position[0];
        int y = position[1];

        GameObject cell = GameObject.Find($"Floor ({x},{y})");

        if (cell != null)
        {
            Debug.Log($"Instanciando humo en la celda: ({x}, {y})");

            // Obtener la posición de la celda
            Vector3 cellPosition = cell.transform.position;

            // Crear la nueva posición ajustada
            float offsetX = 2.019836f; // Desplazamiento en X
            float offsetY = 22.2000008f; // Desplazamiento en Y
            float offsetZ = -3.7f; // Desplazamiento en Z
            Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y + offsetY, cellPosition.z + offsetZ);

            // Instanciar el prefab del fantasma
            GameObject ghost = Instantiate(ghostPrefab, adjustedPosition, Quaternion.identity);

            // Ajustar el tag al instanciar el objeto
            ghost.tag = "Ghost";

            // Ajustar la rotación del fantasma a -180 grados en Y si es necesario
            ghost.transform.rotation = Quaternion.Euler(ghost.transform.rotation.eulerAngles.x, -180, ghost.transform.rotation.eulerAngles.z);

            // Iniciar la corutina para animar el humo
            StartCoroutine(AnimateGhostAppearance(ghost, 2f)); // 2 segundos de duración

            ghost.name = $"Ghost ({x},{y})";
        }
        else
        {
            Debug.LogWarning($"No se encontró la celda en: ({x}, {y})");
        }
    }

    void HandlePortraitAdded(List<int> position)
    {
        // Verificar que la posición sea válida
        if (position == null || position.Count < 2)
        {
            Debug.LogWarning("Posición inválida para agregar un retrato.");
            return;
        }

        int x = position[0];
        int y = position[1];

        GameObject cell = GameObject.Find($"Floor ({x},{y})");

        if (cell != null)
        {
            Debug.Log($"Instanciando retrato en la celda: ({x}, {y})");

            // Obtener la posición de la celda
            Vector3 cellPosition = cell.transform.position;

            // Crear la nueva posición ajustada
            float offsetX = 328.740082f - 321.393524f;
            float offsetY = 42.9823837f - 0f;
            float offsetZ = 32.2999992f - 34.7999992f;

            Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y + offsetY, cellPosition.z + offsetZ);

            // Instanciar el prefab del retrato
            GameObject portrait = Instantiate(portraitPrefab, adjustedPosition, Quaternion.Euler(-90, 0, -26.247f));

            portrait.name = $"Portrait ({x},{y})";

            // Iniciar la corutina para animar el crecimiento
            StartCoroutine(AnimatePortraitGrowth(portrait, 1f)); // Duración de 1 segundo
        }
        else
        {
            Debug.LogWarning($"No se encontró la celda en: ({x}, {y})");
        }
    }

    IEnumerator AnimatePortraitGrowth(GameObject portrait, float duration)
    {
        float elapsedTime = 0f;

        // Tamaño inicial (pequeño)
        Vector3 initialScale = Vector3.zero;

        // Tamaño final (el tamaño original del prefab)
        Vector3 finalScale = portrait.transform.localScale;

        // Asegurarte de que el retrato comience desde el tamaño inicial
        portrait.transform.localScale = initialScale;

        // Animación de crecimiento
        while (elapsedTime < duration)
        {
            elapsedTime += Time.deltaTime;
            float t = Mathf.Clamp01(elapsedTime / duration);

            // Interpolar la escala del retrato
            portrait.transform.localScale = Vector3.Lerp(initialScale, finalScale, t);

            yield return null; // Esperar al siguiente frame
        }

        // Asegurarse de que la escala final sea precisa
        portrait.transform.localScale = finalScale;
    }

    void HandleFireExtinguished(List<int> position)
    {
        if (position == null || position.Count < 2)
        {
            Debug.LogWarning("La posición proporcionada es inválida o incompleta.");
            return;
        }

        int x = position[0]; // Coordenada X
        int y = position[1]; // Coordenada Y

        GameObject ghost = GameObject.Find($"Ghost ({x},{y})");
        if (ghost != null)
        {
            Debug.Log($"Fuego extinguido en ({x}, {y}). Comenzando animación de ghost.");
            StartCoroutine(AnimateReduce(ghost)); // Llama a la animación para el "ghost"
        }
        else
        {
            Debug.LogWarning($"No se encontró el ghost en las coordenadas ({x}, {y}).");
        }
    }

    void HandleSmokeExtinguished(List<int> position)
    {
        if (position == null || position.Count < 2)
        {
            Debug.LogWarning("La posición proporcionada es inválida o incompleta.");
            return;
        }

        int x = position[0]; // Coordenada X
        int y = position[1]; // Coordenada Y

        GameObject smoke = GameObject.Find($"Smoke ({x},{y})");
        if (smoke != null)
        {
            Debug.Log($"Smoke extinguido en ({x}, {y}). Comenzando animación de ghost.");
            StartCoroutine(AnimateReduce(smoke)); // Llama a la animación para el "ghost"
        }
        else
        {
            Debug.LogWarning($"No se encontró el ghost en las coordenadas ({x}, {y}).");
        }
    }

    void HandlePortraitFound(Detail detail)
    {
        int agentId = detail.agent; // ID del agente
        int x = detail.at[0];       // Coordenada X
        int y = detail.at[1];       // Coordenada Y
        string type = detail.portrait_type; // Tipo de retrato

        // Verificar si el agente existe
        if (!agents.TryGetValue(agentId, out GameObject agent))
        {
            Debug.LogWarning($"Agente con ID {agentId} no encontrado.");
            return;
        }

        // Buscar el retrato en la escena
        GameObject mainPortrait = GameObject.Find($"Portrait ({x},{y})");
        if (mainPortrait == null)
        {
            Debug.LogWarning($"No se encontró el retrato en la posición ({x},{y}).");
            return;
        }

        Transform innerPortrait = mainPortrait.transform.Find("Portrait");
        if (innerPortrait == null)
        {
            Debug.LogWarning($"El retrato en ({x},{y}) no contiene un componente 'Portrait'.");
            return;
        }

        Transform mesh4 = innerPortrait.Find("Mesh4");
        if (mesh4 == null)
        {
            Debug.LogWarning($"El retrato en ({x},{y}) no contiene un componente 'Mesh4'.");
            return;
        }

        Renderer renderer = mesh4.GetComponent<Renderer>();
        if (renderer == null)
        {
            Debug.LogWarning($"El componente 'Renderer' no se encontró en 'Mesh4' del retrato en ({x},{y}).");
            return;
        }

        if (type == "Victim")
        {
            // Cambiar material y asignar al agente
            Material randomMaterial = victimMaterials[Random.Range(0, victimMaterials.Length)];
            renderer.material = randomMaterial;

            Debug.Log($"Retrato en ({x},{y}) identificado como 'Victim'. Ahora es hijo de {agent.name}.");

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

            mainPortrait.transform.SetParent(agent.transform); // Asignar como hijo del agente
        }
        else if (type == "False")
        {
            // Cambiar material y destruir después de 2 segundos
            renderer.material = falseMaterial;
            Debug.Log($"Retrato en ({x},{y}) identificado como 'False'. Destruyendo retrato.");
            Destroy(mainPortrait, 2f);
        }
    }

    void HandlePortraitRescued(Detail detail)
    {
        // Construir el nombre del agente a partir del ID
        string agentName = $"Agent_{detail.agent}";

        // Buscar al agente en la escena por su nombre
        GameObject agent = GameObject.Find(agentName);

        if (agent == null)
        {
            Debug.LogWarning($"Agente con nombre {agentName} no encontrado.");
            return;
        }

        // Buscar el retrato como hijo del agente
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
            Destroy(portrait.gameObject); // Eliminar el retrato
        }
        else
        {
            Debug.LogWarning($"El agente {agent.name} no tiene un retrato para rescatar.");
        }
    }


    Vector3 GetFloorPosition(int x, int y)
    {
        GameObject floor = GameObject.Find($"Floor ({x},{y})");
        return floor != null ? floor.transform.position + Vector3.up : Vector3.zero;
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
    public string type;
    public int id;
    public int agent;
    public List<int> from = new List<int>();
    public List<int> to = new List<int>();
    public List<int> position = new List<int>();
    public List<int> target = new List<int>();
    public string portrait_type;
    public List<int> at = new List<int>();
}
