using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class APIConnection : MonoBehaviour
{
    [Header("Prefabs")]
    public GameObject floorPrefab; // Prefab del suelo
    public GameObject ghostPrefab; // Prefab para las víctimas
    public GameObject victimPrefab; // Prefab para las víctimas
    public GameObject fakeAlarmPrefab; // Prefab para las falsas alarmas

    [Header("API Config")]
    public string apiUrl = "http://127.0.0.1:5000/get_board"; // Cambia la URL según tu servidor

    private float floorWidth = 2.276639f; // Ancho del floorPrefab
    private float distanciaX = 48.19f; // Distancia total en X entre los extremos
    private float distanciaY = 34.8f; // Distancia total en Y entre las filas

    void Start()
    {
        StartCoroutine(GetBoardData());
    }

    IEnumerator GetBoardData()
    {
        using (UnityWebRequest request = UnityWebRequest.Get(apiUrl))
        {
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                string json = request.downloadHandler.text;
                Debug.Log("Datos recibidos: " + json);

                BoardData data = JsonConvert.DeserializeObject<BoardData>(json);

                if (data != null)
                {
                    ConstruirTablero(data);
                }
                else
                {
                    Debug.LogError("Error al deserializar los datos del tablero.");
                }
            }
            else
            {
                Debug.LogError("Error al conectar con la API: " + request.error);
            }
        }
    }

    void ConstruirTablero(BoardData data)
    {
        if (data == null)
        {
            Debug.LogError("Los datos del tablero son nulos.");
            return;
        }

        float distanciaXReal = distanciaX - floorWidth;

        // Instanciar el tablero (suelo y paredes)
        for (int y = 0; y < data.height; y++)
        {
            for (int x = 0; x < data.width; x++)
            {
                Vector3 floorPosition = new Vector3(x * distanciaXReal, 0, (data.height - 1 - y) * distanciaY);
                GameObject floor = Instantiate(floorPrefab, floorPosition, Quaternion.Euler(90f, 0f, 0f));
                floor.name = $"Floor ({x + 1},{y + 1})"; // Para que empiece en (1,0) visualmente

                // Obtener las paredes del JSON para esta celda
                WallData wall = data.walls[y][x];

                // Activar/desactivar las paredes de acuerdo a los datos
                ActivarDesactivarParedes(floor, wall);
            }
        }

        // Ahora que las paredes están configuradas, podemos trabajar con las puertas
        InstanciarPuertas(data);
        InstanciarFantasmas(data);
    }

    void ActivarDesactivarParedes(GameObject floor, WallData wall)
    {
        // Buscar los objetos dentro de floorPrefab
        Transform upperWall = floor.transform.Find("UpperWall");
        Transform leftWall = floor.transform.Find("LeftWall");
        Transform rightWall = floor.transform.Find("RightWall");
        Transform bottomWall = floor.transform.Find("BottomWall");

        // Activar o desactivar las paredes según los valores de las paredes
        if (upperWall != null) upperWall.gameObject.SetActive(wall.top == 1);
        if (leftWall != null) leftWall.gameObject.SetActive(wall.left == 1);
        if (rightWall != null) rightWall.gameObject.SetActive(wall.right == 1);
        if (bottomWall != null) bottomWall.gameObject.SetActive(wall.bottom == 1);
    }

    void InstanciarPuertas(BoardData data)
    {
        // Desactivar todas las puertas por defecto
        foreach (var floor in GameObject.FindGameObjectsWithTag("Floor"))
        {
            Transform[] doors = floor.GetComponentsInChildren<Transform>();
            foreach (var door in doors)
            {
                if (door.name.Contains("DoorWall"))
                {
                    door.gameObject.SetActive(false); // Desactivar todas las puertas
                }

                if (door.name.Contains("Entrance"))
                {
                    door.gameObject.SetActive(false); // Desactivar todas las puertas
                }
            }
        }

        // Instanciar puertas activas según los datos del JSON
        foreach (var door in data.doors)
        {
            // Coordenadas base 0 (ajustamos restando 1 a las coordenadas)
            int x1 = door.c1 - 1;
            int y1 = door.r1 - 1;
            int x2 = door.c2 - 1;
            int y2 = door.r2 - 1;

            // Validar que las celdas son adyacentes
            if ((Mathf.Abs(x1 - x2) + Mathf.Abs(y1 - y2)) != 1)
            {
                Debug.LogWarning($"Puerta inválida entre celdas no adyacentes: ({door.c1},{door.r1}) y ({door.c2},{door.r2})");
                continue;
            }

            // Encontrar las celdas afectadas
            GameObject cell1 = GameObject.Find($"Floor ({x1 + 1},{y1 + 1})"); // Sumamos 1 para visualizar correctamente las celdas
            GameObject cell2 = GameObject.Find($"Floor ({x2 + 1},{y2 + 1})");

            // Imprimir el nombre del objeto de las celdas conectadas
            if (cell1 != null && cell2 != null)
            {
                Debug.Log($"Puerta conectada entre los objetos: {cell1.name} y {cell2.name}");

                // Activar/desactivar paredes según la puerta
                if (y1 == y2 && Mathf.Abs(x1 - x2) == 1) // Son celdas adyacentes horizontalmente (misma fila)
                {
                    if (x1 < x2) // Si cell1 está a la izquierda de cell2
                    {
                        // Activar la pared RightDoorWall en cell1 (izquierda) y desactivar RightWall en cell1
                        Transform rightdoorWall = cell1.transform.Find("RightDoorWall");
                        Transform rightWall = cell1.transform.Find("RightWall");
                        Transform leftWall = cell2.transform.Find("LeftWall");

                        if (rightdoorWall != null) rightdoorWall.gameObject.SetActive(true);
                        if (rightWall != null) rightWall.gameObject.SetActive(false);
                        if (leftWall != null) leftWall.gameObject.SetActive(false);
                    }
                    else // Si cell2 está a la izquierda de cell1
                    {
                        // Activar la pared RightDoorWall en cell2 (izquierda) y desactivar RightWall en cell2
                        Transform rightdoorWall = cell2.transform.Find("RightDoorWall");
                        Transform rightWall = cell2.transform.Find("RightWall");
                        Transform leftWall = cell1.transform.Find("LeftWall");

                        if (rightdoorWall != null) rightdoorWall.gameObject.SetActive(true);
                        if (rightWall != null) rightWall.gameObject.SetActive(false);
                        if (leftWall != null) leftWall.gameObject.SetActive(false);
                    }
                }
                else if (x1 == x2 && Mathf.Abs(y1 - y2) == 1) // Son celdas adyacentes verticalmente (misma columna)
                {
                    // Si la puerta es entre celdas adyacentes verticalmente
                    if (y1 < y2) // Si cell2 está abajo de cell1 (y2 > y1)
                    {
                        // Activar la pared BottomDoorWall en cell1 (arriba) y desactivar BottomWall en cell1
                        Transform bottomdoorWall = cell1.transform.Find("BottomDoorWall");
                        Transform bottomWall = cell1.transform.Find("BottomWall");
                        Transform upperWall = cell2.transform.Find("UpperWall");

                        if (bottomdoorWall != null) bottomdoorWall.gameObject.SetActive(true);
                        if (bottomWall != null) bottomWall.gameObject.SetActive(false);
                        if (upperWall != null) upperWall.gameObject.SetActive(false);
                    }
                    else // Si cell1 está abajo de cell2 (y1 > y2)
                    {
                        // Activar la pared BottomDoorWall en cell2 (arriba) y desactivar BottomWall en cell2
                        Transform bottomdoorWall = cell2.transform.Find("BottomDoorWall");
                        Transform bottomWall = cell2.transform.Find("BottomWall");
                        Transform upperWall = cell1.transform.Find("UpperWall");

                        if (bottomdoorWall != null) bottomdoorWall.gameObject.SetActive(true);
                        if (bottomWall != null) bottomWall.gameObject.SetActive(false);
                        if (upperWall != null) upperWall.gameObject.SetActive(false);
                    }
                }
            }
        }
    }

    void InstanciarFantasmas(BoardData data)
    {
        foreach (var fire in data.fires)
        {
            // Ajustar las coordenadas para comenzar desde 0
            int x = fire.col - 1;
            int y = fire.row - 1;

            // Verificar que las coordenadas estén dentro del rango válido
            if (x >= 0 && x < data.width && y >= 0 && y < data.height)
            {
                // Encontrar la celda correspondiente
                GameObject cell = GameObject.Find($"Floor ({x + 1},{y + 1})");

                if (cell != null)
                {
                    Debug.Log($"Instanciando fantasma en la celda: ({x + 1}, {y + 1})");

                    // Obtener la posición de la celda
                    Vector3 cellPosition = cell.transform.position;

                    // Aplicar la transformación personalizada para centrar el fantasma
                    float offsetX = -11.480164f; // Desplazamiento en X
                    float offsetZ = -66f;       // Desplazamiento en Z
                    Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y, cellPosition.z + offsetZ);

                    GameObject ghost = Instantiate(ghostPrefab, adjustedPosition, Quaternion.identity);

                    ghost.transform.Rotate(0, 180, 0, Space.Self);

                    // Nombrar el fantasma para facilitar su identificación
                    ghost.name = $"Ghost ({x + 1},{y + 1})";
                }
                else
                {
                    Debug.LogWarning($"No se encontró la celda en: ({x + 1}, {y + 1})");
                }
            }
            else
            {
                Debug.LogWarning($"Coordenadas fuera de rango: ({fire.row}, {fire.col})");
            }
        }
    }
}

[System.Serializable]
public class BoardData
{
    public int width;
    public int height;
    public List<List<WallData>> walls;
    public List<Door> doors;
    public List<Entrance> entrances;
    public List<Fire> fires;
    public List<FakeAlarm> fake_alarms;
    public List<Victim> victims;
}

[System.Serializable]
public class WallData
{
    public int top;
    public int left;
    public int right;
    public int bottom;
}

[System.Serializable]
public class Door
{
    public int r1;
    public int c1;
    public int r2;
    public int c2;
}

[System.Serializable]
public class Entrance
{
    public int row;
    public int col;
}

[System.Serializable]
public class Fire
{
    public int row;
    public int col;
}

[System.Serializable]
public class FakeAlarm
{
    public int row;
    public int col;
}

[System.Serializable]
public class Victim
{
    public int row;
    public int col;
}
