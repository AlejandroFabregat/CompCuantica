"""
Traductor de Qiskit a PennyLane
Convierte archivos .py con código Qiskit a PennyLane ejecutable
"""

import re
import os

# =============================================================================
# CONFIGURACIÓN - Cambia estas rutas según tus archivos
# =============================================================================
RUTA_ARCHIVO_QISKIT = "Practica1.py"  # Archivo de entrada
RUTA_ARCHIVO_PENNYLANE = "codigo_pennylane.py"  # Archivo de salida

# =============================================================================
# MAPEO DE PUERTAS QISKIT → PENNYLANE
# =============================================================================
GATE_MAPPING = {
    'x': 'qml.PauliX',
    'y': 'qml.PauliY',
    'z': 'qml.PauliZ',
    'h': 'qml.Hadamard',
    'cx': 'qml.CNOT',
    'cy': 'qml.CY',
    'cz': 'qml.CZ',
    'swap': 'qml.SWAP',
    'rx': 'qml.RX',
    'ry': 'qml.RY',
    'rz': 'qml.RZ',
    's': 'qml.S',
    't': 'qml.T',
    'sdg': 'qml.adjoint(qml.S)',
    'tdg': 'qml.adjoint(qml.T)',
    'ccx': 'qml.Toffoli',
    'cswap': 'qml.CSWAP'
}

# =============================================================================
# FUNCIONES DE TRADUCCIÓN
# =============================================================================

def extraer_informacion_circuito(codigo):
    """Extrae información del código Qiskit"""
    lineas = codigo.split('\n')
    
    info = {
        'num_qubits_var': None,
        'num_qubits_literal': None,
        'circuit_var': 'qc',
        'initialize_var': None
    }
    
    for linea in lineas:
        match = re.search(r'(\w+)\s*=\s*int\(np\.log2\(.*?\)\)', linea)
        if match:
            info['num_qubits_var'] = match.group(1)
        
        match = re.search(r'(\w+)\s*=\s*QuantumCircuit\((\d+)\)', linea)
        if match:
            info['circuit_var'] = match.group(1)
            info['num_qubits_literal'] = int(match.group(2))
        
        match = re.search(r'(\w+)\s*=\s*QuantumCircuit\((\w+)\)', linea)
        if match:
            info['circuit_var'] = match.group(1)
            if not info['num_qubits_var']:
                info['num_qubits_var'] = match.group(2)
        
        pattern = rf'{info["circuit_var"]}\.initialize\(([^,]+),'
        match = re.search(pattern, linea)
        if match:
            info['initialize_var'] = match.group(1).strip()
    
    return info

def traducir_funcion_qiskit(codigo_funcion, info):
    """Traduce una función de Qiskit a PennyLane"""
    lineas = codigo_funcion.split('\n')
    nombre_match = re.match(r'def\s+(\w+)\((.*?)\):', lineas[0])
    if not nombre_match:
        return codigo_funcion
    nombre_func = nombre_match.group(1)
    params = nombre_match.group(2)

    # Traducción automática de reconstruir_imagen
    if nombre_func == "reconstruir_imagen":
        return '\n'.join([
            "def reconstruir_imagen(statevector, normalizacion):",
            "    '''Reconstruye la imagen desde el statevector en PennyLane'''",
            "    amplitudes = np.abs(statevector) * normalizacion",
            "    image = amplitudes.reshape((8, 8))",
            "    return image"
        ])

    indent = "    "
    nuevo_codigo = [f"def {nombre_func}({params}):"]

    # Copiar código clásico (sin Qiskit)
    for linea in lineas[1:]:
        stripped = linea.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('for ') and 'range' in stripped:
            continue
        if stripped.startswith("return") and info['circuit_var'] in stripped:
            continue
        if re.search(r'\.(x|y|z|h|cx|cy|cz|swap|rx|ry|rz|initialize)\(', stripped):
            continue
        if any(x in stripped for x in ['QuantumCircuit', 'AerSimulator', 'save_statevector']):
            continue
        nuevo_codigo.append(linea)

    num_qubits = info['num_qubits_literal'] or info['num_qubits_var'] or 'n_qubits'

    # Device + QNode
    nuevo_codigo.append("")
    nuevo_codigo.append(f"{indent}dev = qml.device('default.qubit', wires={num_qubits})")
    nuevo_codigo.append(f"{indent}@qml.qnode(dev)")
    nuevo_codigo.append(f"{indent}def circuit():")
    circuit_indent = indent + "    "

    for linea in lineas[1:]:
        stripped = linea.strip()
        # Initialize
        if f"{info['circuit_var']}.initialize" in stripped:
            nuevo_codigo.append(f"{circuit_indent}qml.AmplitudeEmbedding(")
            nuevo_codigo.append(f"{circuit_indent}    features={info['initialize_var']},")
            nuevo_codigo.append(f"{circuit_indent}    wires=range({num_qubits}),")
            nuevo_codigo.append(f"{circuit_indent}    normalize=False")
            nuevo_codigo.append(f"{circuit_indent})")

        traduccion = traducir_operacion(stripped, info, circuit_indent)
        if traduccion:
            nuevo_codigo.append(traduccion)

    # Return statevector + número de qubits
    nuevo_codigo.append(f"{circuit_indent}return qml.state()")
    nuevo_codigo.append("")
    nuevo_codigo.append(f"{indent}statevector = circuit()")
    nuevo_codigo.append(f"{indent}num_qubits = {num_qubits}")
    nuevo_codigo.append(f"{indent}return statevector, num_qubits, normalizacion")

    return '\n'.join(nuevo_codigo)

def traducir_operacion(linea, info, indent):
    """Traduce una operación individual de Qiskit a PennyLane"""
    circuit_var = info['circuit_var']

    # Puertas de un qubit
    for gate, pl_gate in GATE_MAPPING.items():
        pattern = rf'{circuit_var}\.{gate}\(([^)]+)\)'
        match = re.search(pattern, linea)
        if match:
            qubit = match.group(1).strip()
            return f"{indent}{pl_gate}(wires={qubit})"

    # Puertas de dos qubits
    two_qubit = r'(cx|cy|cz|swap)'
    pattern = rf'{circuit_var}\.({two_qubit})\(([^,]+),\s*([^)]+)\)'
    match = re.search(pattern, linea)
    if match:
        gate = match.group(1)
        q1, q2 = match.group(2).strip(), match.group(3).strip()
        return f"{indent}{GATE_MAPPING[gate]}(wires=[{q1}, {q2}])"

    # Puertas parametrizadas
    param_pattern = rf'{circuit_var}\.(rx|ry|rz)\(([^,]+),\s*([^)]+)\)'
    match = re.search(param_pattern, linea)
    if match:
        gate = match.group(1)
        param, qubit = match.group(2).strip(), match.group(3).strip()
        return f"{indent}{GATE_MAPPING[gate]}({param}, wires={qubit})"

    return None

def generar_main():
    """Genera automáticamente un main para PennyLane usando StatePrep"""
    main_code = [
        "if __name__ == '__main__':",
        "    ruta_imagen = 'paisaje.jpg'  # Reemplaza con tu imagen 8x8",
        "    img_arr = preprocesar_image(ruta_imagen)",
        "    plt.figure(figsize=(8, 4))",
        "    plt.subplot(1, 3, 1)",
        "    plt.imshow(img_arr, cmap='gray')",
        "    plt.title('Original')",
        "    plt.axis('off')",
        "",
        "    img_clasica = inversion_tradiconal(img_arr)",
        "    plt.subplot(1, 3, 2)",
        "    plt.imshow(img_clasica, cmap='gray')",
        "    plt.title('Inversión clásica')",
        "    plt.axis('off')",
        "",
        "    cq, num_qubits, normalizacion = codificar_a_qubits(img_arr)",
        "",
        "    dev = qml.device('default.qubit', wires=num_qubits)",
        "    @qml.qnode(dev)",
        "    def circuito_negativo():",
        "        qml.StatePrep(cq, wires=range(num_qubits))",
        "        for q in range(num_qubits):",
        "            qml.PauliX(wires=q)",
        "        return qml.state()",
        "",
        "    cq_neg = circuito_negativo()",
        "    img_cuantica = reconstruir_imagen(cq_neg, normalizacion)",
        "    plt.subplot(1, 3, 3)",
        "    plt.imshow(img_cuantica, cmap='gray')",
        "    plt.title('Negativo cuántico')",
        "    plt.axis('off')",
        "",
        "    plt.tight_layout()",
        "    plt.show()"
    ]
    return '\n'.join(main_code)

def traducir_codigo_completo(codigo_qiskit):
    """Traduce el código completo de Qiskit a PennyLane"""
    info = extraer_informacion_circuito(codigo_qiskit)

    # Separar en funciones
    funciones = re.split(r'\n(?=def\s+\w+)', codigo_qiskit)
    codigo_traducido = []

    # Header
    codigo_traducido.append("# Código traducido de Qiskit a PennyLane")
    codigo_traducido.append("# Generado automáticamente\n")
    codigo_traducido.append("import pennylane as qml")
    codigo_traducido.append("import numpy as np")
    codigo_traducido.append("import matplotlib.pyplot as plt")
    codigo_traducido.append("from PIL import Image")
    codigo_traducido.append("import time\n")

    # Traducir funciones
    for seccion in funciones:
        if seccion.strip().startswith('def'):
            codigo_traducido.append(traducir_funcion_qiskit(seccion, info))
        elif seccion.strip() and not any(x in seccion for x in ['import', 'from']):
            codigo_traducido.append(seccion)
    
    # Agregar main
    codigo_traducido.append(generar_main())

    return '\n'.join(codigo_traducido)

# =============================================================================
# EJECUCIÓN PRINCIPAL DEL TRADUCTOR
# =============================================================================
def main():
    if not os.path.exists(RUTA_ARCHIVO_QISKIT):
        print(f"❌ ERROR: No se encontró el archivo '{RUTA_ARCHIVO_QISKIT}'")
        return

    with open(RUTA_ARCHIVO_QISKIT, 'r', encoding='utf-8') as f:
        codigo_qiskit = f.read()

    print("⚙️  Traduciendo código a PennyLane...")
    codigo_pennylane = traducir_codigo_completo(codigo_qiskit)

    with open(RUTA_ARCHIVO_PENNYLANE, 'w', encoding='utf-8') as f:
        f.write(codigo_pennylane)

    print(f"✅ Traducción completada. Archivo generado: {RUTA_ARCHIVO_PENNYLANE}")

if __name__ == "__main__":
    main()
