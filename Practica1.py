# -------------------------------------------------------------
# IMPORTACIONES PARA AMBOS METODOS
# -------------------------------------------------------------
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import time

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
def aplicar_quantum_negativo(cq, num_qubits):
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

    sim = AerSimulator(method='statevector')    #Crea un simulador para que devuelva vectores de estado completos
    correr_cq = cq.copy()                       # Hacemos una copia y eliminamos medidas finales si existen 
                                                #(las medidas impiden obtener statevector)
    try:
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
            # Si falla, dejamos cq_nuevo como estaba y seguiremos intentando
            pass

    statevector = None
    # Intentar guardar explícitamente el estado del vector (más robusto entre versiones de Aer)
    try:
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
            statevector = result.get_statevector(0)
        except Exception:
            try:
                statevector = result.get_statevector()
            except Exception:
                # Fallback a result.data()
                try:
                    data = result.data()
                    statevector = data.get('statevector', None)
                except Exception:
                    statevector = None
    except Exception:
        statevector = None

    if statevector is None:
        raise RuntimeError("No se pudo obtener el statevector del resultado del simulador. Asegúrate de que el circuito no tenga medidas y que 'qiskit-aer' esté instalado y actualizado.")

    # Obtener amplitudes en valores de intensidad 0..1
    amplitudes = np.abs(statevector) * normalizacion
    image = amplitudes.reshape((8, 8))
    return image

# -------------------------------------------------------------
# 3) Ejecucuion completa
# -------------------------------------------------------------

if __name__ == "__main__":
    path = "paisaje.jpg"   # Cambia la ruta a tu imagen

    arr_original = preprocesar_image(path)
    cq, num_qubits, normalizacion = codificar_a_qubits(arr_original)

    t_clasico_inicio = time.time()
    arr_inverso_tradicional = inversion_tradiconal(arr_original)
    t_clasico_fin = time.time()
    tiempo_clasico = t_clasico_fin - t_clasico_inicio

    t_cuantico_inicio = time.time()
    aplicar_quantum_negativo(cq, num_qubits)
    arr_inverso_cuantico = reconstruir_imagen(cq, normalizacion)
    t_cuantico_fin = time.time()
    tiempo_cuantico = t_cuantico_fin - t_cuantico_inicio

    # Mostrar ambas imágenes
    fig, ax = plt.subplots(1, 3)
    ax[0].set_title("Original (8x8)")
    ax[0].imshow(arr_original, cmap="gray")

    ax[1].set_title(f"Inversión tradicional: {tiempo_clasico:.4f} s")
    ax[1].imshow(arr_inverso_tradicional, cmap="gray")

    ax[2].set_title(f"Inversión cuántica: {tiempo_cuantico:.4f} s")
    ax[2].imshow(arr_inverso_cuantico, cmap="gray")

    plt.show()