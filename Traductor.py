"""
Traductor de Qiskit a PennyLane
Convierte archivos .py con código Qiskit a PennyLane ejecutable
"""

import re
import os

# =============================================================================
# CONFIGURACIÓN - Cambia estas rutas según tus archivos
# =============================================================================
RUTA_ARCHIVO_QISKIT = "../PRACTICA_1/Practica1.py"  # Archivo de entrada
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
        'initialize_var': None,
        'funciones': [],
        'operaciones': []
    }
    
    # Detectar variables y circuitos
    for linea in lineas:
        # Variable de qubits
        match = re.search(r'(\w+)\s*=\s*int\(np\.log2\(.*?\)\)', linea)
        if match:
            info['num_qubits_var'] = match.group(1)
        
        # QuantumCircuit con literal
        match = re.search(r'(\w+)\s*=\s*QuantumCircuit\((\d+)\)', linea)
        if match:
            info['circuit_var'] = match.group(1)
            info['num_qubits_literal'] = int(match.group(2))
        
        # QuantumCircuit con variable
        match = re.search(r'(\w+)\s*=\s*QuantumCircuit\((\w+)\)', linea)
        if match:
            info['circuit_var'] = match.group(1)
            if not info['num_qubits_var']:
                info['num_qubits_var'] = match.group(2)
        
        # Initialize
        pattern = rf'{info["circuit_var"]}\.initialize\(([^,]+),'
        match = re.search(pattern, linea)
        if match:
            info['initialize_var'] = match.group(1).strip()
    
    return info

def traducir_funcion_qiskit(codigo_funcion, info):
    """Traduce una función de Qiskit a PennyLane (sin for vacíos)"""
    lineas = codigo_funcion.split('\n')

    # Extraer nombre de función
    match = re.match(r'def\s+(\w+)\((.*?)\):', lineas[0])
    if not match:
        return codigo_funcion

    nombre_func = match.group(1)
    params = match.group(2)

    # Detectar operaciones cuánticas
    if not any(re.search(r'\.(x|y|z|h|cx|rx|ry|rz|initialize)\(', l) for l in lineas):
        return codigo_funcion

    indent = "    "
    nuevo_codigo = [f"def {nombre_func}({params}):"]

    # -------------------------------------------------
    # 1️⃣ Copiar código clásico
    # -------------------------------------------------
    for linea in lineas[1:]:
        stripped = linea.strip()

        if not stripped or stripped.startswith('#'):
            continue

        # ❌ No copiar bucles for del Qiskit
        if stripped.startswith('for ') and 'range' in stripped:
            continue

        # ❌ No copiar returns tipo: return cq, ...
        if stripped.startswith("return") and info['circuit_var'] in stripped:
            continue

        if re.search(r'\.(x|y|z|h|cx|cy|cz|swap|rx|ry|rz|initialize)\(', stripped):
            continue
        if any(x in stripped for x in ['QuantumCircuit', 'AerSimulator', 'save_statevector']):
            continue

        nuevo_codigo.append(linea)

    num_qubits = info['num_qubits_literal'] or info['num_qubits_var'] or 'n_qubits'

    # -------------------------------------------------
    # 2️⃣ Device + QNode
    # -------------------------------------------------
    nuevo_codigo.append("")
    nuevo_codigo.append(f"{indent}dev = qml.device('default.qubit', wires={num_qubits})")
    nuevo_codigo.append(f"{indent}@qml.qnode(dev)")
    nuevo_codigo.append(f"{indent}def circuit():")

    circuit_indent = indent + "    "

    i = 1
    while i < len(lineas):
        stripped = lineas[i].strip()

        # -------- for loop --------
        loop_match = re.match(r'for\s+(\w+)\s+in\s+range\(([^)]+)\):', stripped)
        if loop_match:
            loop_var, range_val = loop_match.groups()
            nuevo_codigo.append(f"{circuit_indent}for {loop_var} in range({range_val}):")

            inner_indent = circuit_indent + "    "
            i += 1
            contenido = False

            while i < len(lineas) and lineas[i].startswith(("        ", "\t\t")):
                inner = lineas[i].strip()
                traduccion = traducir_operacion(inner, info, inner_indent)
                if traduccion:
                    nuevo_codigo.append(traduccion)
                    contenido = True
                i += 1

            if not contenido:
                nuevo_codigo.append(f"{inner_indent}pass")

            continue

        # -------- initialize --------
        if f"{info['circuit_var']}.initialize" in stripped:
            nuevo_codigo.append(f"{circuit_indent}qml.AmplitudeEmbedding(")
            nuevo_codigo.append(f"{circuit_indent}    features={info['initialize_var']},")
            nuevo_codigo.append(f"{circuit_indent}    wires=range({num_qubits}),")
            nuevo_codigo.append(f"{circuit_indent}    normalize=False")
            nuevo_codigo.append(f"{circuit_indent})")

        # -------- operación normal --------
        traduccion = traducir_operacion(stripped, info, circuit_indent)
        if traduccion:
            nuevo_codigo.append(traduccion)

        i += 1

    # -------------------------------------------------
    # 3️⃣ Return
    # -------------------------------------------------
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
    codigo_traducido.append("AerSimulator = None  # Placeholder para compatibilidad Qiskit\n")

    
    # Traducir cada sección
    for seccion in funciones:
        if seccion.strip().startswith('def'):
            traducido = traducir_funcion_qiskit(seccion, info)
            codigo_traducido.append(traducido)
            codigo_traducido.append("")
        elif seccion.strip() and not any(x in seccion for x in ['import', 'from']):
            # Mantener código no funcional (main, etc)
            codigo_traducido.append(seccion)
    
    return '\n'.join(codigo_traducido)

# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 60)
    print("TRADUCTOR QISKIT → PENNYLANE")
    print("=" * 60)
    
    # Verificar que existe el archivo
    if not os.path.exists(RUTA_ARCHIVO_QISKIT):
        print(f"\n❌ ERROR: No se encontró el archivo '{RUTA_ARCHIVO_QISKIT}'")
        print(f"   Asegúrate de que la ruta sea correcta.\n")
        return
    
    # Leer código Qiskit
    print(f"\n📖 Leyendo archivo: {RUTA_ARCHIVO_QISKIT}")
    with open(RUTA_ARCHIVO_QISKIT, 'r', encoding='utf-8') as f:
        codigo_qiskit = f.read()
    
    # Traducir
    print(f"⚙️  Traduciendo código a PennyLane...")
    codigo_pennylane = traducir_codigo_completo(codigo_qiskit)
    
    # Guardar
    print(f"💾 Guardando archivo: {RUTA_ARCHIVO_PENNYLANE}")
    with open(RUTA_ARCHIVO_PENNYLANE, 'w', encoding='utf-8') as f:
        f.write(codigo_pennylane)
    
    print(f"\n✅ ¡Traducción completada exitosamente!")
    print(f"   Archivo generado: {RUTA_ARCHIVO_PENNYLANE}")
    print(f"   Puedes ejecutarlo con: python {RUTA_ARCHIVO_PENNYLANE}\n")
    print("=" * 60)

if __name__ == "__main__":
    main()