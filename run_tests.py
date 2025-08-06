"""
Script para ejecutar todas las pruebas del sistema de gestión de fondos
"""

import os
import sys
import subprocess
from pathlib import Path

def run_tests():
    """
    Ejecuta todas las pruebas con pytest y genera reportes
    """
    print("🧪 EJECUTANDO PRUEBAS DEL SISTEMA DE GESTIÓN DE FONDOS")
    print("=" * 60)
    
    # Cambiar al directorio del backend
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Instalar dependencias si es necesario
    print("📦 Instalando dependencias de testing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-django", "pytest-mock", "factory-boy"], 
                   check=False, capture_output=True)
    
    # Configurar variables de entorno para testing
    os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
    
    print("\n🔬 Ejecutando pruebas...")
    
    # Comandos de pytest con diferentes opciones
    test_commands = [
        # Pruebas básicas con verbose
        [
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--disable-warnings"
        ],
        
        # Pruebas con marcadores específicos
        [
            sys.executable, "-m", "pytest", 
            "tests/test_business_rules.py", 
            "-v", 
            "-m", "not slow",
            "--tb=line"
        ],
        
        # Pruebas de integración
        [
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "-m", "integration",
            "--tb=short"
        ]
    ]
    
    results = []
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n📋 Ejecución {i}: {' '.join(cmd[3:])}")
        print("-" * 40)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            results.append({
                'command': ' '.join(cmd[3:]),
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            print(result.stdout)
            if result.stderr:
                print("⚠️ Warnings/Errors:")
                print(result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout - Las pruebas tardaron más de 2 minutos")
            results.append({
                'command': ' '.join(cmd[3:]),
                'return_code': -1,
                'stdout': '',
                'stderr': 'Timeout after 120 seconds'
            })
        except Exception as e:
            print(f"❌ Error ejecutando pruebas: {e}")
            results.append({
                'command': ' '.join(cmd[3:]),
                'return_code': -2,
                'stdout': '',
                'stderr': str(e)
            })
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    total_runs = len(results)
    successful_runs = sum(1 for r in results if r['return_code'] == 0)
    
    for i, result in enumerate(results, 1):
        status = "✅ EXITOSO" if result['return_code'] == 0 else "❌ FALLIDO"
        print(f"{i}. {result['command']}: {status}")
    
    print(f"\n📈 Total: {successful_runs}/{total_runs} ejecuciones exitosas")
    
    if successful_runs == total_runs:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
        return True
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar los detalles arriba.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
