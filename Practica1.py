# -------------------------------------------------------------
# IMPORTACIONES PARA AMBOS METODOS
# -------------------------------------------------------------
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# -------------------------------------------------------------
# IMPORTACIONES PARA METODO CUANTICO
# -------------------------------------------------------------
from qiskit import QuantumCircuit
try:
    from qiskit_aer import AerSimulator
except Exception:
    try:
        # Older import location
        from qiskit.providers.aer import AerSimulator
    except Exception:
        AerSimulator = None


# -------------------------------------------------------------
# 0) Cargar imagen, convertir a escala de grises y reducir a 8x8 (PARA AMBOS METODOS)
# -------------------------------------------------------------
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

    cq = QuantumCircuit(num_qubits)                 #Crea un circuito cuántico

    # Iniciamos el estado cuántico con esas amplitudes
    cq.initialize(flat, cq.qubits)

    return cq, num_qubits, normalizacion

# -----------------------METODO CUANTICO-----------------------
# 2) Aplicar filtro cuántico negativo (Puerta X a todos los qubits)
# -------------------------------------------------------------
def applicar_quantum_negativo(cq, num_qubits):
    for q in range(num_qubits):
        cq.x(q)   # Puerta NOT cuántica

# -----------------------METODO CUANTICO-----------------------
# 3) Medir y reconstruir la imagen procesada
# -------------------------------------------------------------
def reconstruir_imagen(cq, normalizacion):
    if AerSimulator is None:
        raise ImportError(
            "No se encontró AerSimulator. Instala 'qiskit-aer' (por ejemplo: pip install qiskit-aer) "
            "o instala qiskit con extras: pip install 'qiskit[visualization]'."
        )

    sim = AerSimulator(method='statevector')
    # Hacemos una copia y eliminamos medidas finales si existen (las medidas impiden obtener statevector)
    correr_cq = cq.copy()
    try:
        # Método conveniente si está disponible
        correr_cq.remove_final_measurements()
    except Exception:
        # Fallback: construir nuevo circuito sin instrucciones de medida
        try:
            from qiskit.circuit.instruction import Instruction
            cq_nuevo = QuantumCircuit(correr_cq.num_qubits)
            for instr, qargs, cargs in correr_cq.data:
                # Omitir instrucciones de medida
                if instr.name == 'measure':
                    continue
                cq_nuevo.append(instr, qargs, cargs)
            correr_cq = cq_nuevo
        except Exception:
            # Si falla, dejamos qc_run como estaba y seguiremos intentando
            pass

    stado_vector = None
    # Intentar guardar explícitamente el statevector (más robusto entre versiones de Aer)
    try:
        # save_statevector puede no existir en versiones antiguas, así que lo intentamos en try
        cq_sv = correr_cq.copy()
        try:
            cq_sv.save_statevector()
        except Exception:
            # Algunos backends requieren etiqueta
            try:
                cq_sv.save_statevector(label='statevector')
            except Exception:
                pass
        job = sim.run(cq_sv)
        result = job.result()
        # Intentar obtener por índice de experimento (0)
        try:
            estado_vector = result.get_statevector(0)
        except Exception:
            try:
                estado_vector = result.get_statevector()
            except Exception:
                # Fallback a result.data()
                try:
                    data = result.data()
                    estado_vector = data.get('statevector', None)
                except Exception:
                    estado_vector = None
    except Exception:
        estado_vector = None

    if estado_vector is None:
        raise RuntimeError("No se pudo obtener el statevector del resultado del simulador. Asegúrate de que el circuito no tenga medidas y que 'qiskit-aer' esté instalado y actualizado.")

    # Obtener amplitudes en valores de intensidad 0..1
    amplitudes = np.abs(estado_vector) * normalizacion
    image = amplitudes.reshape((8, 8))
    return image

# -------------------------------------------------------------
# 3) Ejecucuion completa
# -------------------------------------------------------------

if __name__ == "__main__":
    path = "paisaje.jpg"   # Cambia la ruta a tu imagen

    arr_original = preprocesar_image(path)
    cq, num_qubits, normalizacion = codificar_a_qubits(arr_original)

    arr_inverso_tradicional = inversion_tradiconal(arr_original)

    applicar_quantum_negativo(cq, num_qubits)
    arr_inverso_cuantico = reconstruir_imagen(cq, normalizacion)

    # Mostrar ambas imágenes
    fig, ax = plt.subplots(1, 3)
    ax[0].set_title("Original (8x8)")
    ax[0].imshow(arr_original, cmap="gray")

    ax[1].set_title("Inversion tradicional")
    ax[1].imshow(arr_inverso_tradicional, cmap="gray")

    ax[2].set_title("Inversion cuantica")
    ax[2].imshow(arr_inverso_cuantico, cmap="gray")

    plt.show()