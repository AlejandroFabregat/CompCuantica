# Código traducido de Qiskit a PennyLane
# Generado automáticamente

import pennylane as qml
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import time

def preprocesar_image(path):
    img = Image.open(path).convert("L")      # Escala de grises
    img = img.resize((8, 8))                # Reducir tamaño a 8x8
    img_arr = np.array(img) / 255.0             # Normalizar entre 0 y 1
    return img_arr

    dev = qml.device('default.qubit', wires=num_qubits)
    @qml.qnode(dev)
    def circuit():
        return qml.state()

    statevector = circuit()
    num_qubits = num_qubits
    return statevector, num_qubits, normalizacion
def inversion_tradiconal(img_arr):
    rotacion_clasica = img_arr[::-1, ::-1]
    return rotacion_clasica

    dev = qml.device('default.qubit', wires=num_qubits)
    @qml.qnode(dev)
    def circuit():
        return qml.state()

    statevector = circuit()
    num_qubits = num_qubits
    return statevector, num_qubits, normalizacion
def codificar_a_qubits(img_arr):
    flat = img_arr.flatten()                            #Convierte la imagen en un vector unidimensional
    normalizacion = np.sqrt(np.sum(flat**2))        # Normalización para amplitudes (Calcula la norma Euclidiana)
    flat = flat / normalizacion                     # Qiskit requiere esto
    num_pixeles = len(flat) 
    num_qubits = int(np.log2(num_pixeles))           # 8x8 = 64 → 6 qubits

    dev = qml.device('default.qubit', wires=num_qubits)
    @qml.qnode(dev)
    def circuit():
        qml.AmplitudeEmbedding(
            features=flat,
            wires=range(num_qubits),
            normalize=False
        )
        return qml.state()

    statevector = circuit()
    num_qubits = num_qubits
    return statevector, num_qubits, normalizacion
def aplicar_quantum_negativo(cq, num_qubits):

    dev = qml.device('default.qubit', wires=num_qubits)
    @qml.qnode(dev)
    def circuit():
        qml.PauliX(wires=q)
        return qml.state()

    statevector = circuit()
    num_qubits = num_qubits
    return statevector, num_qubits, normalizacion
def reconstruir_imagen(statevector, normalizacion):
    '''Reconstruye la imagen desde el statevector en PennyLane'''
    amplitudes = np.abs(statevector) * normalizacion
    image = amplitudes.reshape((8, 8))
    return image
if __name__ == '__main__':
    ruta_imagen = 'paisaje.jpg'  # Reemplaza con tu imagen 8x8
    img_arr = preprocesar_image(ruta_imagen)
    plt.figure(figsize=(8, 4))
    plt.subplot(1, 3, 1)
    plt.imshow(img_arr, cmap='gray')
    plt.title('Original')
    plt.axis('off')

    img_clasica = inversion_tradiconal(img_arr)
    plt.subplot(1, 3, 2)
    plt.imshow(img_clasica, cmap='gray')
    plt.title('Inversión clásica')
    plt.axis('off')

    cq, num_qubits, normalizacion = codificar_a_qubits(img_arr)

    dev = qml.device('default.qubit', wires=num_qubits)
    @qml.qnode(dev)
    def circuito_negativo():
        qml.StatePrep(cq, wires=range(num_qubits))
        for q in range(num_qubits):
            qml.PauliX(wires=q)
        return qml.state()

    cq_neg = circuito_negativo()
    img_cuantica = reconstruir_imagen(cq_neg, normalizacion)
    plt.subplot(1, 3, 3)
    plt.imshow(img_cuantica, cmap='gray')
    plt.title('Negativo cuántico')
    plt.axis('off')

    plt.tight_layout()
    plt.show()

    print("Imagen original:\n", img_arr)
    print("Imagen negativa cuántica:\n", img_cuantica)  