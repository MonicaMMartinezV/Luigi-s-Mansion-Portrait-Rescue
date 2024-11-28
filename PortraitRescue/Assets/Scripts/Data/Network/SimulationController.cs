using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using System.IO;
using TMPro;

public class SimulationController : MonoBehaviour
{
    public GameObject rescuerPrefab;
    public GameObject firefighterPrefab;
    public GameObject smokePrefab;
    public GameObject ghostPrefab;
    public GameObject portraitPrefab;
    public Material falseMaterial;
    public Material[] victimMaterials;

    public TextMeshProUGUI casualtiesCounter;
    public TextMeshProUGUI damageCounter;
    public TextMeshProUGUI savedCounter;

    public int casualties = 0;
    public int damage = 0;
    public int saved = 0;

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

                // Guardar el JSON en un archivo
                string filePath = Path.Combine(Application.persistentDataPath, "simulationData.json");
                try
                {
                    File.WriteAllText(filePath, json);
                    Debug.Log("JSON guardado en: " + filePath);
                }
                catch (System.Exception e)
                {
                    Debug.LogError("Error al guardar el archivo: " + e.Message);
                }

                // Deserializar y continuar con la lógica de simulación
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
            Debug.Log($"Procesando evento: {step.type}");

            HandleDetail(step);
            totalDetailsProcessed++;

            yield return new WaitForSeconds(1f); // Pausa de 1 segundo entre eventos
        }

        Debug.Log($"Simulación completada. Total de eventos procesados: {totalDetailsProcessed}");
    }

    void HandleDetail(Step step)
    {
        switch (step.type)
        {
            case "agent_move":
                HandleAgentMove(step.agent,step.from,step.to);
                break;
            case "smoke_added":
                HandleSmokeAdded(step.position);
                break;
            case "found_portrait":
                HandlePortraitFound(step.at,step.agent,step.portrait_type);
                break;
            case "fire_extinguished":
                HandleFireExtinguished(step.at);
                break;
            case "portrait_added":
                HandlePortraitAdded(step.position);
                break;
            case "fire_removed_to_portrait":
                HandleFireExtinguished(step.position);
                break;
            case "rescued_portrait":
                HandlePortraitRescued(step);
                break;
            case "wall_destroyed":
                HandleWallDestroyed(step.position,step.target,step.damage);
                break;
            case "fire_to_smoke":
                HandleFireExtinguished(step.at);
                HandleSmokeAdded(step.position);
                break;
            case "smoke_extinguished":
                HandleSmokeExtinguished(step.position);
                break;
            case "smoke_to_fire":
                HandleSmokeExtinguished(step.position);
                HandleFireAdded(step.position);
                break; 
            case "open_door":
                HandleDoorOpened(step.position, step.target);
                break; 
            case "fire_extended":
                HandleFireAdded(step.to);
                break;
            case "damage_wall":
                HandleWallDamaged(step.position, step.target,step.damage);
                break;
            case "portrait_lost":
                HandlePortraitLost(step.position);
                break;
            default:
                Debug.LogWarning($"Evento no manejado: {step.type}");
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

    bool IsValidPosition(List<int> position)
    {
        return position != null && position.Count >= 2;
    }

    List<string> GetWallTypes(List<int> from, List<int> to)
    {
        // Si from y to son iguales, devolver todas las paredes
        if (from[0] == to[0] && from[1] == to[1])
        {
            return new List<string> { "UpperWall", "BottomWall", "LeftWall", "RightWall" };
        }

        // Caso normal: devuelve una sola pared
        if (from[0] == to[0])  // Mismo X (Vertical)
        {
            return new List<string> { from[1] > to[1] ? "UpperWall" : "BottomWall" };
        }
        else if (from[1] == to[1])  // Mismo Y (Horizontal)
        {
            return new List<string> { from[0] > to[0] ? "LeftWall" : "RightWall" };
        }

        // Retornar lista vacía si no aplica ningún caso
        return new List<string>();
    }


    void DestroyWallAtPosition(List<int> position, string wallType)
    {
        GameObject floor = GameObject.Find($"Floor ({position[0]},{position[1]})");
        if (floor != null)
        {
            Transform wallTransform = floor.transform.Find(wallType);
            if (wallTransform != null)
            {
                if (wallType.Contains("Wall"))  // Solo destruir si es una pared válida
                {
                    Destroy(wallTransform.gameObject);
                    Debug.Log($"Destruyendo {wallType} en Floor ({position[0]},{position[1]}).");
                }
            }
            else
            {
                Debug.LogWarning($"No se encontró {wallType} en Floor ({position[0]},{position[1]}).");
            }
        }
        else
        {
            Debug.LogWarning($"No se encontró Floor en la posición ({position[0]},{position[1]}).");
        }
    }

    void ChangeWallColorAtPosition(List<int> position, string wallType, Color color)
    {
        GameObject floor = GameObject.Find($"Floor ({position[0]},{position[1]})");
        if (floor != null)
        {
            Transform wallTransform = floor.transform.Find(wallType);
            if (wallTransform != null)
            {
                Renderer renderer = wallTransform.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.material.color = color;
                    Debug.Log($"Cambiado el color de {wallType} en Floor ({position[0]},{position[1]}) a {color}.");
                }
                else
                {
                    Debug.LogWarning($"Renderer no encontrado en {wallType} de Floor ({position[0]},{position[1]}).");
                }
            }
            else
            {
                Debug.LogWarning($"No se encontró {wallType} en Floor ({position[0]},{position[1]}).");
            }
        }
        else
        {
            Debug.LogWarning($"No se encontró Floor en la posición ({position[0]},{position[1]}).");
        }
    }

    void UpdateDamageCounter()
    {
        if (damageCounter != null)
        {
            damageCounter.text = $"Damage: {damage}";
        }
    }

    void HandleWallDestroyed(List<int> position, List<int> target, int damage_counter)
    {
        if (!IsValidPosition(position) || !IsValidPosition(target))
        {
            Debug.LogError("Position o Target inválidos en HandleWallDestroyed.");
            return;
        }

        // Obtener las paredes para la posición y el target
        List<string> wallTypesFromPosition = GetWallTypes(position, target);

        // Destruir las paredes en `position`
        foreach (string wallType in wallTypesFromPosition)
        {
            DestroyWallAtPosition(position, wallType);
        }

        // Obtener las paredes para `target`
        List<string> wallTypesFromTarget = GetWallTypes(target, position);
        foreach (string wallType in wallTypesFromTarget)
        {
            DestroyWallAtPosition(target, wallType);
        }

        // Actualizar el contador de daño
        damage = damage_counter;
        UpdateDamageCounter();
    }


    void HandleWallDamaged(List<int> position, List<int> target, int damage_counter)
    {
        if (!IsValidPosition(position) || !IsValidPosition(target))
        {
            Debug.LogError("Position o Target inválidos en HandleWallDamaged.");
            return;
        }

        // Obtener las paredes para la posición
        List<string> wallTypesFromPosition = GetWallTypes(position, target);
        foreach (string wallType in wallTypesFromPosition)
        {
            ChangeWallColorAtPosition(position, wallType, Color.red);
        }

        // Obtener las paredes para `target`
        List<string> wallTypesFromTarget = GetWallTypes(target, position);
        foreach (string wallType in wallTypesFromTarget)
        {
            ChangeWallColorAtPosition(target, wallType, Color.red);
        }

        // Actualizar el contador de daño
        damage = damage_counter;
        UpdateDamageCounter();
    }

    IEnumerator CameraShake(float duration = 0.2f, float magnitude = 0.1f)
    {
        Vector3 originalPosition = Camera.main.transform.localPosition;

        float elapsed = 0f;

        while (elapsed < duration)
        {
            float xOffset = Random.Range(-1f, 1f) * magnitude;
            float yOffset = Random.Range(-1f, 1f) * magnitude;

            Camera.main.transform.localPosition = originalPosition + new Vector3(xOffset, yOffset, 0);

            elapsed += Time.deltaTime;

            yield return null;
        }

        Camera.main.transform.localPosition = originalPosition;
    }


    void HandleDoorOpened(List<int> position, List<int> target)
    {
        if (position == null || position.Count < 2)
        {
            Debug.LogError("Position inválida o nula en HandleDoorOpened.");
            return;
        }

        if (target == null || target.Count < 2)
        {
            Debug.LogError("Target inválido o nulo en HandleDoorOpened.");
            return;
        }

        int xPos = position[0];
        int yPos = position[1];
        int xTarget = target[0];
        int yTarget = target[1];

        string doorTypeFromPosition = "";
        string doorTypeFromTarget = "";

        // Determinar el tipo de puerta en `position`
        if (xPos == xTarget)  // Mismo X (Vertical)
        {
            if (yTarget < yPos)
            {
                doorTypeFromPosition = "UpperDoorWall";
                doorTypeFromTarget = "BottomDoorWall";
            }
            else if (yTarget > yPos)
            {
                doorTypeFromPosition = "BottomDoorWall";
                doorTypeFromTarget = "UpperDoorWall";
            }
        }
        else if (yPos == yTarget)  // Mismo Y (Horizontal)
        {
            if (xTarget > xPos)
            {
                doorTypeFromPosition = "RightDoorWall";
                doorTypeFromTarget = "LeftDoorWall";
            }
            else if (xTarget < xPos)
            {
                doorTypeFromPosition = "LeftDoorWall";
                doorTypeFromTarget = "RightDoorWall";
            }
        }

        Debug.Log($"Posición: ({xPos},{yPos}), Target: ({xTarget},{yTarget}), DoorTypeFromPosition: {doorTypeFromPosition}, DoorTypeFromTarget: {doorTypeFromTarget}");

        // Abrir la puerta en "position"
        GameObject floorPosition = GameObject.Find($"Floor ({xPos},{yPos})");
        //GameObject doorPosition = GameObject.Find($"Puerta ({xPos}, {yPos})");
        if (floorPosition != null)
        {
            Transform doorTransform = floorPosition.transform.Find(doorTypeFromPosition);
            if (doorTransform != null)
            {
                Debug.Log($"Abriendo {doorTypeFromPosition} en Floor ({xPos},{yPos})");
                // Iniciar la corutina para animar la puerta
                StartCoroutine(AnimateDoorOpening(doorTransform.gameObject, 2f)); // 2 segundos de duración
            }
            else
            {
                Debug.LogWarning($"No se encontró el {doorTypeFromPosition} dentro de Floor ({xPos},{yPos}).");
            }
        }
        else
        {
            Debug.LogWarning($"No se encontró Floor en la posición ({xPos},{yPos}).");
        }

        // Abrir la puerta en "target"
        GameObject floorTarget = GameObject.Find($"Floor ({xTarget},{yTarget})");
        //GameObject doorTarget = GameObject.Find($"Puerta ({xTarget}, {yTarget})");

        if (floorTarget != null)
        {
            Transform doorTransform = floorTarget.transform.Find(doorTypeFromTarget);
            if (doorTransform != null)
            {
                Debug.Log($"Abriendo {doorTypeFromTarget} en Floor ({xTarget},{yTarget})");
                // Iniciar la corutina para animar la puerta
                StartCoroutine(AnimateDoorOpening(doorTransform.gameObject, 2f)); // 2 segundos de duración
            }
            else
            {
                Debug.LogWarning($"No se encontró el {doorTypeFromTarget} dentro de Floor ({xTarget},{yTarget}).");
            }
        }
        else
        {
            Debug.LogWarning($"No se encontró Floor en la posición ({xTarget},{yTarget}).");
        }
    }

    void HandlePortraitLost(List<int> position)
    {
        
        if (position == null || position.Count < 2)
        {
            Debug.LogError("Position inválida o nula en HandlePortraitLost.");
            return;
        }
        
        int x = position[0];
        int y = position[1];

        // Buscar el retrato en la escena
        GameObject mainPortrait = GameObject.Find($"Portrait ({x},{y})");

        if (mainPortrait == null)
        {
            Debug.LogWarning($"No se encontró el retrato en la posición ({x},{y}).");
            return;
        }

        // Actualizar contador
        casualties++;
        if (casualtiesCounter != null)
        {
            casualtiesCounter.text = $"Casualties: {casualties}";
        }
        
        // Destruir el retrato en "position"
        Destroy(mainPortrait, 2f);
    }

    void HandleAgentMove(int agentId, List<int> from, List<int> to)
    {
        string agentName = $"Agent_{agentId}";
        GameObject agent = GameObject.Find(agentName);

        if (agent == null)
        {
            Debug.LogWarning($"Agente con nombre {agentName} no encontrado.");
            return;
        }

        Vector3 fromPosition = GetFloorPosition(from[0], from[1]);
        Vector3 toPosition = GetFloorPosition(to[0], to[1]);

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

    IEnumerator AnimateDoorOpening(GameObject door, float duration)
    {
        float elapsedTime = 0f;

        // Posiciones iniciales y finales
        Vector3 startPosition = door.transform.position;
        Vector3 targetPosition = startPosition + new Vector3(0, -10f, 0); // Cuánto baja la puerta

        // Animar el traslado
        while (elapsedTime < duration)
        {
            float t = elapsedTime / duration;

            // Interpolación para el traslado
            door.transform.position = Vector3.Lerp(startPosition, targetPosition, t);

            elapsedTime += Time.deltaTime;

            // Esperar el siguiente frame
            yield return null;
        }

        // Asegurar la posición final
        door.transform.position = targetPosition;
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

    void HandlePortraitFound(List<int> at, int agentID, string portrait_type)
    {
        int agentId = agentID; // ID del agente
        int x = at[0];       // Coordenada X
        int y = at[1];       // Coordenada Y
        string type = portrait_type; // Tipo de retrato

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

        if (type == "victim")
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

    void HandlePortraitRescued(Step step)
    {
        // Construir el nombre del agente a partir del ID
        string agentName = $"Agent_{step.agent}";

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
            
            // Actualizar contador
            saved++;
            if (savedCounter != null)
            {
                savedCounter.text = $"Saved: {saved}";
            }

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
    public int agent;
    public List<int> from;
    public List<int> to;
    public List<int> at;
    public List<int> target;
    public List<int> position;
    public int step;
    public int damage;
    public string type;
    public string portrait_type;
}

