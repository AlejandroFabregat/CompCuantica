# -------------------------------------------------------------
# IMPORTACIONES
# -------------------------------------------------------------
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import pennylane as qml
import time

# -------------------------------------------------------------
# 0) Cargar imagen, convertir a escala de grises y reducir a 8x8
# -------------------------------------------------------------
def preprocesar_image(path):
    img = Image.open(path).convert("L")  # Escala de grises
    img = img.resize((8, 8))             # Reducir tamaño
    img_arr = np.array(img) / 255.0      # Normalizar
    return img_arr

# -----------------------METODO CLASICO------------------------
def inversion_tradiconal(img_arr):
    return img_arr[::-1, ::-1]  # rotación 180º


# -----------------------METODO CUANTICO-----------------------
# 1) Codificar la imagen en amplitudes
# -------------------------------------------------------------
def codificar_a_qubits(img_arr):
    flat = img_arr.flatten()
    normalizacion = np.sqrt(np.sum(flat**2))
    flat = flat / normalizacion         # Normalize to unit vector

    num_pixeles = len(flat)             # 64
    num_qubits = int(np.log2(num_pixeles))   # 6

    return flat, num_qubits, normalizacion

# -----------------------METODO CUANTICO-----------------------
# 2) Aplicar filtro negativo usando puertas X
# -------------------------------------------------------------
def circuito_negativo(flat, num_qubits):
    dev = qml.device("default.qubit", wires=num_qubits)

    @qml.qnode(dev)
    def circuit():
        qml.AmplitudeEmbedding(features=flat, wires=range(num_qubits), normalize=False)
        # Aplicar NOT cuántico a todos los qubits
        for q in range(num_qubits):
            qml.PauliX(wires=q)
        return qml.state()

    return circuit()

# -----------------------METODO CUANTICO-----------------------
# 3) Reconstrucción de la imagen
# -------------------------------------------------------------
def reconstruir_imagen(statevector, normalizacion):
    amplitudes = np.abs(statevector) * normalizacion
    image = amplitudes.reshape((8, 8))
    return image


# -------------------------------------------------------------
# EJECUCIÓN
# -------------------------------------------------------------
if __name__ == "__main__":
    path = "paisaje.jpg"   

    arr_original = preprocesar_image(path)

    t_clasico_inicio = time.time()
    arr_inverso_tradicional = inversion_tradiconal(arr_original)
    t_clasico_fin = time.time()
    tiempo_clasico = t_clasico_fin - t_clasico_inicio

    t_cuantico_inicio = time.time()
    flat, num_qubits, normalizacion = codificar_a_qubits(arr_original)
    estado_final = circuito_negativo(flat, num_qubits)
    arr_inverso_cuantico = reconstruir_imagen(estado_final, normalizacion)
    t_cuantico_fin = time.time()
    tiempo_cuantico = t_cuantico_fin - t_cuantico_inicio


    fig, ax = plt.subplots(1, 3)
    ax[0].set_title("Original (8x8)")
    ax[0].imshow(arr_original, cmap="gray")

    ax[1].set_title(f"Inversión tradicional: {tiempo_clasico:.4f} s")
    ax[1].imshow(arr_inverso_tradicional, cmap="gray")

    ax[2].set_title(f"Inversión cuántica(pennylane): {tiempo_cuantico:.4f} s")
    ax[2].imshow(arr_inverso_cuantico, cmap="gray")

    plt.show()
