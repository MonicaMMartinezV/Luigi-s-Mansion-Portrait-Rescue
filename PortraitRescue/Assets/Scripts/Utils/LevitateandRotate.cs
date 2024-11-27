using UnityEngine;

public class LevitateAndRotate : MonoBehaviour
{
    // Amplitud del movimiento vertical
    public float amplitude = 0.5f;

    // Frecuencia del movimiento vertical
    public float frequency = 1f;

    // Velocidad de rotación sobre el eje Z
    public float rotationSpeed = 45f;

    // Posición inicial para mantener el desplazamiento vertical sin alteraciones
    private Vector3 startPosition;

    void Start()
    {
        // Guardar la posición inicial del objeto (solo para el eje Y)
        startPosition = transform.position;
    }

    void Update()
    {
        // Calcular el desplazamiento en el eje Y utilizando una onda sinusoidal
        float offsetY = Mathf.Sin(Time.time * frequency) * amplitude;

        // Actualizar la posición del objeto solo en el eje Y
        transform.position = new Vector3(startPosition.x, startPosition.y + offsetY, startPosition.z);

        // Rotar sobre el eje Z sin afectar el desplazamiento
        transform.Rotate(0, 0, rotationSpeed * Time.deltaTime);
    }
}
