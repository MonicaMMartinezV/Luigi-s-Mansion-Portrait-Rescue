using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Levitation : MonoBehaviour
{
    // Amplitud del movimiento vertical
    public float amplitude = 0.5f;

    // Frecuencia del movimiento
    public float frequency = 1f;

    // Posición inicial
    private Vector3 startPosition;

    void Start()
    {
        // Guardar la posición inicial del objeto
        startPosition = transform.position;
    }

    void Update()
    {
        // Calcular el desplazamiento en el eje Y utilizando una onda sinusoidal
        float offsetY = Mathf.Sin(Time.time * frequency) * amplitude;

        // Actualizar la posición del objeto
        transform.position = startPosition + new Vector3(0, offsetY, 0);
    }
}
