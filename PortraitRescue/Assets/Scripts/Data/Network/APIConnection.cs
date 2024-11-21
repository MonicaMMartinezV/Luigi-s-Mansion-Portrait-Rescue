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
    public GameObject portraitPrefab; // Prefab para las falsas alarmas

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
        InstanciarFalseAlarms(data);
        InstanciarVictims(data);
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
        // Desactivar todas las puertas y entradas por defecto
        foreach (var floor in GameObject.FindGameObjectsWithTag("Floor"))
        {
            foreach (Transform child in floor.transform)
            {
                if (child.name.Contains("DoorWall") || child.name.Contains("Entrance"))
                {
                    child.gameObject.SetActive(false); // Desactivar todas las puertas y entradas
                }
            }
        }

        // Activar puertas según los datos del JSON
        foreach (var door in data.doors)
        {
            // Coordenadas base 0
            int x1 = door.c1 - 1;
            int y1 = door.r1 - 1;
            int x2 = door.c2 - 1;
            int y2 = door.r2 - 1;

            // Validar que las celdas son adyacentes
            if (Mathf.Abs(x1 - x2) + Mathf.Abs(y1 - y2) != 1)
            {
                Debug.LogWarning($"Puerta inválida entre celdas no adyacentes: ({door.c1},{door.r1}) y ({door.c2},{door.r2})");
                continue;
            }

            // Obtener las celdas afectadas
            GameObject cell1 = GameObject.Find($"Floor ({x1 + 1},{y1 + 1})");
            GameObject cell2 = GameObject.Find($"Floor ({x2 + 1},{y2 + 1})");

            if (cell1 == null || cell2 == null)
            {
                Debug.LogWarning($"No se encontraron celdas para la puerta: ({door.c1},{door.r1}) - ({door.c2},{door.r2})");
                continue;
            }

            // Activar las puertas entre las celdas
            if (y1 == y2) // Mismo renglón (horizontal)
            {
                if (x1 < x2) // cell1 a la izquierda de cell2
                    ActivarPuerta(cell1, "RightDoorWall", "RightWall", cell2, "LeftWall");
                else // cell2 a la izquierda de cell1
                    ActivarPuerta(cell2, "RightDoorWall", "RightWall", cell1, "LeftWall");
            }
            else if (x1 == x2) // Misma columna (vertical)
            {
                if (y1 < y2) // cell1 arriba de cell2
                    ActivarPuerta(cell1, "BottomDoorWall", "BottomWall", cell2, "UpperWall");
                else // cell2 arriba de cell1
                    ActivarPuerta(cell2, "BottomDoorWall", "BottomWall", cell1, "UpperWall");
            }
        }

        // Activar entradas según los datos del JSON
        foreach (var entrance in data.entrances)
        {
            int x = entrance.col - 1;
            int y = entrance.row - 1;

            GameObject cell = GameObject.Find($"Floor ({x + 1},{y + 1})");
            if (cell == null)
            {
                Debug.LogWarning($"No se encontró la celda para la entrada: ({entrance.col},{entrance.row})");
                continue;
            }

            // Activar la entrada según la posición
            if (y == 0)
                ActivarEntrada(cell, "UpperEntrance", "UpperWall", "UpperDoorWall");
            else if (x == 0)
                ActivarEntrada(cell, "LeftEntrance", "LeftWall", "LeftDoorWall");
            else if (y == data.height - 1)
                ActivarEntrada(cell, "BottomEntrance", "BottomWall", "BottomDoorWall");
            else if (x == data.width - 1)
                ActivarEntrada(cell, "RightEntrance", "RightWall", "RightDoorWall");
        }
    }

    void ActivarPuerta(GameObject cell1, string puerta1, string pared1, GameObject cell2, string pared2)
    {
        // Activar la puerta en cell1 y desactivar paredes relevantes
        Transform door1 = cell1.transform.Find(puerta1);
        Transform wall1 = cell1.transform.Find(pared1);
        Transform wall2 = cell2.transform.Find(pared2);

        if (door1 != null) door1.gameObject.SetActive(true);
        if (wall1 != null) wall1.gameObject.SetActive(false);
        if (wall2 != null) wall2.gameObject.SetActive(false);
    }

    void ActivarEntrada(GameObject cell, string entrada, string pared, string puerta)
    {
        Transform entrance = cell.transform.Find(entrada);
        Transform wall = cell.transform.Find(pared);
        Transform doorWall = cell.transform.Find(puerta);

        if (entrance != null) entrance.gameObject.SetActive(true);
        if (wall != null) wall.gameObject.SetActive(false);
        if (doorWall != null) doorWall.gameObject.SetActive(false);
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

                    // Aplicar la transformación personalizada para posicionar correctamente el fantasma
                    float offsetX = 2.019836f; // Desplazamiento en X
                    float offsetY = 22.2000008f; // Desplazamiento en Y
                    float offsetZ = -3.7f; // Desplazamiento en Z
                    Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y + offsetY, cellPosition.z + offsetZ);

                    // Instanciar el prefab del fantasma
                    GameObject ghost = Instantiate(ghostPrefab, adjustedPosition, Quaternion.identity);

                    // Ajustar el tag al instanciar el objeto
                    ghost.tag = "Ghost";

                    // Nombrar el fantasma para facilitar su identificación
                    ghost.name = $"Ghost ({x + 1},{y + 1})";

                    // Ajustar la rotación del fantasma a -180 grados en Y si es necesario
                    ghost.transform.rotation = Quaternion.Euler(ghost.transform.rotation.eulerAngles.x, -180, ghost.transform.rotation.eulerAngles.z);
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


    void InstanciarFalseAlarms(BoardData data)
    {
        foreach (var fake in data.fake_alarms)
        {
            // Ajustar las coordenadas para comenzar desde 0
            int x = fake.col - 1;
            int y = fake.row - 1;

            // Verificar que las coordenadas estén dentro del rango válido
            if (x >= 0 && x < data.width && y >= 0 && y < data.height)
            {
                // Encontrar la celda correspondiente
                GameObject cell = GameObject.Find($"Floor ({x + 1},{y + 1})");

                if (cell != null)
                {
                    Debug.Log($"Instanciando fake alarm en la celda: ({x + 1}, {y + 1})");

                    // Obtener la posición de la celda
                    Vector3 cellPosition = cell.transform.position;

                    // Aplicar la transformación personalizada para posicionar correctamente el retrato
                    float offsetX = -15.34008f; // Desplazamiento en X
                    float offsetY = 84.5999985f; // Desplazamiento en Y
                    float offsetZ = 21.7f; // Desplazamiento en Z
                    Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y + offsetY, cellPosition.z + offsetZ);

                    // Instanciar el prefab del retrato
                    GameObject portrait = Instantiate(portraitPrefab, adjustedPosition, Quaternion.Euler(-90, 0, -26.247f));

                    // Ajustar el tag al instanciar el objeto
                    portrait.tag = "FalseAlarm";

                    // Nombrar el retrato para facilitar su identificación
                    portrait.name = $"Portrait ({x + 1},{y + 1})";
                }
                else
                {
                    Debug.LogWarning($"No se encontró la celda en: ({x + 1}, {y + 1})");
                }
            }
            else
            {
                Debug.LogWarning($"Coordenadas fuera de rango: ({fake.row}, {fake.col})");
            }
        }
    }

    void InstanciarVictims(BoardData data)
    {
        foreach (var victim in data.victims)
        {
            // Ajustar las coordenadas para comenzar desde 0
            int x = victim.col - 1;
            int y = victim.row - 1;

            // Verificar que las coordenadas estén dentro del rango válido
            if (x >= 0 && x < data.width && y >= 0 && y < data.height)
            {
                // Encontrar la celda correspondiente
                GameObject cell = GameObject.Find($"Floor ({x + 1},{y + 1})");

                if (cell != null)
                {
                    Debug.Log($"Instanciando fake alarm en la celda: ({x + 1}, {y + 1})");

                    // Obtener la posición de la celda
                    Vector3 cellPosition = cell.transform.position;

                    // Aplicar la transformación personalizada para posicionar correctamente el retrato
                    float offsetX = -15.34008f; // Desplazamiento en X
                    float offsetY = 84.5999985f; // Desplazamiento en Y
                    float offsetZ = 21.7f; // Desplazamiento en Z
                    Vector3 adjustedPosition = new Vector3(cellPosition.x + offsetX, cellPosition.y + offsetY, cellPosition.z + offsetZ);

                    // Instanciar el prefab del retrato
                    GameObject portrait = Instantiate(portraitPrefab, adjustedPosition, Quaternion.Euler(-90, 0, -26.247f));

                    // Ajustar el tag al instanciar el objeto
                    portrait.tag = "Victim";

                    // Nombrar el retrato para facilitar su identificación
                    portrait.name = $"Portrait ({x + 1},{y + 1})";
                }
                else
                {
                    Debug.LogWarning($"No se encontró la celda en: ({x + 1}, {y + 1})");
                }
            }
            else
            {
                Debug.LogWarning($"Coordenadas fuera de rango: ({victim.row}, {victim.col})");
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
