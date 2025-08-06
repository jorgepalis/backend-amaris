"""
Script simplificado para diagnosticar y configurar DynamoDB
"""

import os
import sys
import django

# Añadir el directorio actual al path para poder importar core
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.append(project_dir)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from funds.models import Fund, UserBalance, Transaction, User, UserFund, UserNotifications
from datetime import datetime


def test_aws_connection():
    """Probar la conexión a AWS"""
    print("🔄 Probando conexión a AWS...")
    try:
        import boto3
        dynamodb = boto3.client('dynamodb', region_name=settings.AWS_DEFAULT_REGION)
        response = dynamodb.list_tables()
        print(f"✅ Conexión exitosa. Tablas existentes: {response.get('TableNames', [])}")
        return True
    except Exception as e:
        print(f"❌ Error de conexión a AWS: {e}")
        return False


def migrate_user_fund_table():
    """Migrar la tabla UserFund para añadir campos nuevos sin perder datos"""
    print("\n🔄 Verificando migración de tabla UserFund...")
    
    try:
        # Verificar si la tabla existe
        if not UserFund.exists():
            print("ℹ️  Tabla UserFund no existe, se creará nueva")
            return False
        
        # Verificar si ya tiene el campo invested_amount
        print("Verificando estructura de tabla UserFund...")
        
        # Obtener una muestra de registros para verificar estructura
        try:
            sample_records = list(UserFund.scan(limit=1))
            if sample_records:
                sample_record = sample_records[0]
                # Verificar si ya tiene invested_amount
                if hasattr(sample_record, 'invested_amount') and sample_record.invested_amount is not None:
                    print("✅ Tabla UserFund ya tiene el campo invested_amount")
                    return True
                else:
                    print("🔄 Tabla UserFund necesita migración para añadir invested_amount")
                    return migrate_user_fund_data()
            else:
                print("ℹ️  Tabla UserFund está vacía, no necesita migración")
                return True
        except Exception as e:
            print(f"❌ Error verificando estructura: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        return False


def migrate_user_fund_data():
    """Migrar datos existentes añadiendo el campo invested_amount"""
    print("🔄 Migrando datos de UserFund...")
    
    try:
        # Obtener todos los registros existentes
        existing_records = list(UserFund.scan())
        migrated_count = 0
        
        for record in existing_records:
            try:
                # Solo migrar si no tiene invested_amount o es None
                if not hasattr(record, 'invested_amount') or record.invested_amount is None:
                    # Usar subscription_amount como invested_amount por defecto
                    record.invested_amount = record.subscription_amount
                    record.updated_at = datetime.utcnow()
                    record.save()
                    migrated_count += 1
                    
            except Exception as e:
                print(f"❌ Error migrando registro {record.user_id}-{record.fund_id}: {e}")
                continue
        
        print(f"✅ Migración completada: {migrated_count} registros actualizados")
        return True
        
    except Exception as e:
        print(f"❌ Error en migración de datos: {e}")
        return False


def create_tables_simple():
    """Crear tablas una por una para diagnosticar"""
    print("\n🔄 Creando tablas individualmente...")
    
    tables = [
        ('User', User),
        ('Fund', Fund), 
        ('UserBalance', UserBalance),
        ('Transaction', Transaction),
        ('UserFund', UserFund),  # Nueva tabla agregada
        ('UserNotifications', UserNotifications)  # Nueva tabla para preferencias de notificación
    ]
    
    for name, model in tables:
        try:
            print(f"Verificando tabla {name}...")
            exists = model.exists()
            print(f"¿Tabla {name} existe? {exists}")
            
            if not exists:
                print(f"Creando tabla {name}...")
                model.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
                print(f"✅ Tabla {name} creada exitosamente")
            else:
                print(f"ℹ️  Tabla {name} ya existe")
                
                # Si es UserFund, verificar migración
                if name == 'UserFund':
                    migrate_user_fund_table()
                
        except Exception as e:
            print(f"❌ Error con tabla {name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


def initialize_data_simple():
    """Inicializar datos de forma simple"""
    print("\n🔄 Inicializando datos...")
    
    try:
        # Crear usuario por defecto
        print("Creando usuario por defecto...")
        user = User.get_default_user()
        print(f"✅ Usuario: {user.name}")
        
        # Crear saldo
        print("Creando saldo de usuario...")
        balance = UserBalance.get_or_create_balance(user.user_id)
        print(f"✅ Saldo: ${balance.available_balance}")
        
        # Crear preferencias de notificación
        print("Creando preferencias de notificación...")
        notifications = UserNotifications.get_or_create_preferences(user.user_id)
        print(f"✅ Preferencias: {notifications.notification_type}")
        
        # Verificar fondos
        print("Verificando fondos existentes...")
        funds_count = len(list(Fund.scan(limit=1)))
        
        if funds_count == 0:
            print("Creando fondos por defecto...")
            Fund.initialize_default_funds()
            print("✅ Fondos creados")
        else:
            print("ℹ️  Fondos ya existen")
            
        return True
        
    except Exception as e:
        print(f"❌ Error inicializando datos: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal con diagnóstico"""
    print("🚀 Diagnóstico y configuración de DynamoDB...")
    print(f"📍 Región: {settings.AWS_DEFAULT_REGION}")
    print(f"📋 Prefijo: {settings.DYNAMODB_TABLE_PREFIX}")
    print(f"🔑 AWS Key ID: {settings.AWS_ACCESS_KEY_ID[:10]}..." if settings.AWS_ACCESS_KEY_ID else "❌ Sin AWS Key")
    
    # Paso 1: Probar conexión
    if not test_aws_connection():
        return False
    
    # Paso 2: Crear tablas
    if not create_tables_simple():
        return False
    
    # Paso 3: Inicializar datos
    if not initialize_data_simple():
        return False
    
    print("\n🎉 ¡Configuración completada exitosamente!")
    return True


if __name__ == "__main__":
    main()
