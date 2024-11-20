using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class APIConnection : MonoBehaviour
{
    [Header("Prefabs")]
    public GameObject floorPrefab; // Prefab del suelo
    public GameObject victimPrefab; // Prefab para las víctimas
    public GameObject fakeAlarmPrefab; // Prefab para las falsas alarmas
    public GameObject doorPrefab; // Prefab para las puertas

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

        for (int y = 0; y < data.height; y++)
        {
            for (int x = 0; x < data.width; x++)
            {
                // Iniciar en la esquina superior izquierda (1, 0)
                Vector3 floorPosition = new Vector3(x * distanciaXReal, 0, (data.height - 1 - y) * distanciaY);
                GameObject floor = Instantiate(floorPrefab, floorPosition, Quaternion.Euler(90f, 0f, 0f));
                floor.name = $"Floor ({x + 1},{y})"; // Para que empiece en (1,0) visualmente

                // Obtener las paredes del JSON para esta celda
                WallData wall = data.walls[y][x];

                // Activar/desactivar las paredes de acuerdo a los datos
                ActivarDesactivarParedes(floor, wall);
            }
        }

        InstanciarObjetosInteres(data, distanciaXReal, distanciaY);
    }

    void ActivarDesactivarParedes(GameObject floor, WallData wall)
    {
        // Buscar los objetos dentro de floorPrefab
        Transform upperWall = floor.transform.Find("UpperWall");
        Transform leftWall = floor.transform.Find("LeftWall");
        Transform rightWall = floor.transform.Find("RightWall");
        Transform bottomWall = floor.transform.Find("BottomWall");

        // Activar o desactivar los objetos según los valores de las paredes
        if (upperWall != null) upperWall.gameObject.SetActive(wall.top == 1);
        if (leftWall != null) leftWall.gameObject.SetActive(wall.left == 1);
        if (rightWall != null) rightWall.gameObject.SetActive(wall.right == 1);
        if (bottomWall != null) bottomWall.gameObject.SetActive(wall.bottom == 1);
    }

    void InstanciarObjetosInteres(BoardData data, float distanciaXReal, float distanciaY)
    {
        // Instanciar las víctimas
        foreach (var victim in data.victims)
        {
            Vector3 victimPosition = new Vector3(victim.col * distanciaXReal, 0, (data.height - 1 - victim.row) * distanciaY);
            Instantiate(victimPrefab, victimPosition, Quaternion.identity);
        }

        // Instanciar falsas alarmas
        foreach (var fakeAlarm in data.fake_alarms)
        {
            Vector3 fakeAlarmPosition = new Vector3(fakeAlarm.col * distanciaXReal, 0, (data.height - 1 - fakeAlarm.row) * distanciaY);
            Instantiate(fakeAlarmPrefab, fakeAlarmPosition, Quaternion.identity);
        }

        // Instanciar puertas
        foreach (var door in data.doors)
        {
            Vector3 doorPosition = new Vector3(door.c1 * distanciaXReal, 0, (data.height - 1 - door.r1) * distanciaY);
            Instantiate(doorPrefab, doorPosition, Quaternion.identity);
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
    public int bottom;
    public int right;
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
