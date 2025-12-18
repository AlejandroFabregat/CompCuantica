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


# -----------------------METODO CLASICO------------------------
# 1) Girar 180°
# -------------------------------------------------------------

def inversion_tradiconal(img_arr):
    rotacion_clasica = img_arr[::-1, ::-1]
    return rotacion_clasica


# -----------------------METODO CUANTICO-----------------------
# 1) Codificar la imagen en un circuito cuántico (amplitude encoding)
# -------------------------------------------------------------

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
        for q in range(num_qubits):
            qml.PauliX(wires=q)
        return qml.state()

    statevector = circuit()
    num_qubits = num_qubits
    return statevector, num_qubits, normalizacion

def reconstruir_imagen(statevector, normalizacion):
    '''Reconstruye la imagen desde el statevector en PennyLane'''
    amplitudes = np.abs(statevector) * normalizacion
    image = amplitudes.reshape((8, 8))  # ajusta tamaño si es otra resolución
    return image
