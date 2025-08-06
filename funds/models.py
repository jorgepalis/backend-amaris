from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, 
    NumberAttribute, 
    BooleanAttribute, 
    UTCDateTimeAttribute
)
from pynamodb.indexes import LocalSecondaryIndex, GlobalSecondaryIndex, AllProjection
from django.conf import settings
from decimal import Decimal
import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Create your PynamoDB models here.

class User(Model):
    """
    Modelo PynamoDB para representar la información del usuario único
    """
    class Meta:
        table_name = f"{settings.DYNAMODB_TABLE_PREFIX}users"
        region = settings.AWS_DEFAULT_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    # Clave primaria
    user_id = UnicodeAttribute(hash_key=True)
    
    # Información del usuario
    name = UnicodeAttribute()
    email = UnicodeAttribute()
    phone = UnicodeAttribute()
    document_number = UnicodeAttribute()
    document_type = UnicodeAttribute(default='CC')  # CC, TI, CE, etc.
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    @classmethod
    def get_default_user(cls) -> 'User':
        """Obtener o crear el usuario por defecto del sistema"""
        default_user_id = "user_default"
        
        try:
            return cls.get(default_user_id)
        except cls.DoesNotExist:
            # Crear usuario por defecto si no existe
            user = cls(
                user_id=default_user_id,
                name="Cliente de Prueba",
                email="palis963@hotmail.com",
                phone="+573163789817",
                document_number="1234567890",
                document_type="CC",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            user.save()
            return user
    
    def to_dict(self) -> Dict:
        """Convertir el modelo a diccionario"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'document_number': self.document_number,
            'document_type': self.document_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Fund(Model):
    """
    Modelo PynamoDB para representar los fondos de inversión
    """
    class Meta:
        table_name = f"{settings.DYNAMODB_TABLE_PREFIX}funds"
        region = settings.AWS_DEFAULT_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    # Clave primaria
    id = UnicodeAttribute(hash_key=True)
    
    # Atributos del fondo
    name = UnicodeAttribute()
    minimum_amount = NumberAttribute()  # Monto mínimo para vincularse
    category = UnicodeAttribute()       # FPV o FIC
    is_active = BooleanAttribute(default=True)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    @classmethod
    def create_fund(cls, name: str, minimum_amount: Decimal, category: str):
        """Crear un nuevo fondo"""
        fund_id = str(uuid.uuid4())
        return cls(
            id=fund_id,
            name=name,
            minimum_amount=float(minimum_amount),
            category=category,
            is_active=True
        )
    
    @classmethod
    def get_active_funds(cls) -> List['Fund']:
        """Obtener todos los fondos activos"""
        return [fund for fund in cls.scan() if fund.is_active]
    
    @classmethod
    def initialize_default_funds(cls):
        """Inicializar los fondos por defecto según la prueba técnica"""
        default_funds = [
            {
                'name': 'FPV_EL CLIENTE_RECAUDADORA',
                'minimum_amount': Decimal('75000'),
                'category': 'FPV'
            },
            {
                'name': 'FPV_EL CLIENTE_ECOPETROL',
                'minimum_amount': Decimal('125000'),
                'category': 'FPV'
            },
            {
                'name': 'DEUDAPRIVADA',
                'minimum_amount': Decimal('50000'),
                'category': 'FIC'
            },
            {
                'name': 'FDO-ACCIONES',
                'minimum_amount': Decimal('250000'),
                'category': 'FIC'
            },
            {
                'name': 'FPV_EL CLIENTE_DINAMICA',
                'minimum_amount': Decimal('100000'),
                'category': 'FPV'
            }
        ]
        
        for fund_data in default_funds:
            fund = cls.create_fund(**fund_data)
            fund.save()
    
    def to_dict(self) -> Dict:
        """Convertir el modelo a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'minimum_amount': str(self.minimum_amount),
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserBalance(Model):
    """
    Modelo PynamoDB para representar el saldo disponible del usuario
    """
    class Meta:
        table_name = f"{settings.DYNAMODB_TABLE_PREFIX}user_balances"
        region = settings.AWS_DEFAULT_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    # Clave primaria
    user_id = UnicodeAttribute(hash_key=True)
    
    # Atributos del saldo
    available_balance = NumberAttribute()
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    @classmethod
    def create_user_balance(cls, user_id: str, initial_balance: Decimal = Decimal('500000.00')):
        """Crear saldo inicial para un usuario"""
        return cls(
            user_id=user_id,
            available_balance=float(initial_balance),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @classmethod
    def get_or_create_balance(cls, user_id: str) -> 'UserBalance':
        """Obtener o crear el saldo de un usuario"""
        try:
            return cls.get(user_id)
        except cls.DoesNotExist:
            balance = cls.create_user_balance(user_id)
            balance.save()
            return balance
    
    def update_balance(self, new_balance: Decimal) -> bool:
        """Actualizar el saldo del usuario"""
        try:
            self.available_balance = float(new_balance)
            self.updated_at = datetime.utcnow()
            self.save()
            return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict:
        """Convertir el modelo a diccionario"""
        return {
            'user_id': self.user_id,
            'available_balance': str(self.available_balance),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserTransactionIndex(GlobalSecondaryIndex):
    """
    Índice secundario global para consultar transacciones por usuario y fecha
    """
    class Meta:
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    user_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class Transaction(Model):
    """
    Modelo PynamoDB para representar las transacciones
    """
    class Meta:
        table_name = f"{settings.DYNAMODB_TABLE_PREFIX}transactions"
        region = settings.AWS_DEFAULT_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    # Clave primaria
    id = UnicodeAttribute(hash_key=True)
    
    # Atributos de la transacción
    user_id = UnicodeAttribute()
    fund_id = UnicodeAttribute()
    transaction_type = UnicodeAttribute()  # SUBSCRIPTION o CANCELLATION
    amount = NumberAttribute()
    status = UnicodeAttribute(default='PENDING')  # PENDING, COMPLETED, FAILED
    notification_sent = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    # Índice para consultas por usuario
    user_index = UserTransactionIndex()
    
    @classmethod
    def create_transaction(cls, user_id: str, fund_id: str, transaction_type: str, 
                          amount: Decimal, status: str = 'PENDING'):
        """Crear una nueva transacción"""
        transaction_id = str(uuid.uuid4())
        return cls(
            id=transaction_id,
            user_id=user_id,
            fund_id=fund_id,
            transaction_type=transaction_type,
            amount=float(amount),
            status=status,
            notification_sent=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @classmethod
    def get_user_transactions(cls, user_id: str, limit: int = 10) -> List['Transaction']:
        """Obtener las últimas transacciones de un usuario"""
        try:
            return list(cls.user_index.query(
                user_id, 
                scan_index_forward=False,  # Orden descendente por fecha
                limit=limit
            ))
        except Exception:
            return []
    
    def update_status(self, status: str) -> bool:
        """Actualizar el estado de una transacción"""
        try:
            self.status = status
            self.updated_at = datetime.utcnow()
            self.save()
            return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict:
        """Convertir el modelo a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'fund_id': self.fund_id,
            'transaction_type': self.transaction_type,
            'amount': str(self.amount),
            'status': self.status,
            'notification_sent': self.notification_sent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserFund(Model):
    """
    Modelo PynamoDB para representar las suscripciones de usuarios a fondos
    Tabla de relación para facilitar consultas y cálculos
    """
    class Meta:
        table_name = f"{settings.DYNAMODB_TABLE_PREFIX}user_funds"
        region = settings.AWS_DEFAULT_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    # Claves primarias
    user_id = UnicodeAttribute(hash_key=True)
    fund_id = UnicodeAttribute(range_key=True)
    
    # Atributos de la suscripción
    subscribed_at = UTCDateTimeAttribute()
    cancelled_at = UTCDateTimeAttribute(null=True)
    active = BooleanAttribute(default=True)
    subscription_amount = NumberAttribute()  # Monto con el que se suscribió
    invested_amount = NumberAttribute()      # Valor realmente invertido (puede ser diferente al monto de suscripción)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    @classmethod
    def create_subscription(cls, user_id: str, fund_id: str, amount: Decimal, invested_amount: Optional[Decimal] = None):
        """Crear una nueva suscripción"""
        # Si no se especifica invested_amount, usar el amount
        if invested_amount is None:
            invested_amount = amount
            
        return cls(
            user_id=user_id,
            fund_id=fund_id,
            subscribed_at=datetime.utcnow(),
            active=True,
            subscription_amount=float(amount),
            invested_amount=float(invested_amount),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @classmethod
    def get_user_active_funds(cls, user_id: str) -> List['UserFund']:
        """Obtener todos los fondos activos de un usuario"""
        try:
            # Consultar todas las suscripciones del usuario
            subscriptions = list(cls.query(user_id))
            # Filtrar solo las activas
            return [sub for sub in subscriptions if sub.active]
        except Exception:
            return []
    
    @classmethod
    def get_subscription(cls, user_id: str, fund_id: str) -> Optional['UserFund']:
        """Obtener una suscripción específica"""
        try:
            return cls.get(user_id, fund_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def is_user_subscribed(cls, user_id: str, fund_id: str) -> bool:
        """Verificar si un usuario está suscrito activamente a un fondo"""
        subscription = cls.get_subscription(user_id, fund_id)
        return subscription is not None and subscription.active
    
    @classmethod
    def can_user_subscribe(cls, user_id: str, fund_id: str) -> tuple[bool, str]:
        """
        Verificar si un usuario puede suscribirse a un fondo
        Retorna (puede_suscribirse, mensaje_error)
        """
        subscription = cls.get_subscription(user_id, fund_id)
        
        if subscription is None:
            return True, ""
        
        if subscription.active:
            return False, f"Ya tiene una suscripción activa a este fondo"
        
        # Si tiene una suscripción inactiva, puede reactivarla
        return True, "Suscripción anterior encontrada - se reactivará"
    
    def cancel_subscription(self) -> bool:
        """Marcar la suscripción como cancelada"""
        try:
            self.active = False
            self.cancelled_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.save()
            return True
        except Exception:
            return False
    
    def reactivate_subscription(self) -> bool:
        """Reactivar una suscripción cancelada"""
        try:
            self.active = True
            self.cancelled_at = None
            self.updated_at = datetime.utcnow()
            self.save()
            return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict:
        """Convertir el modelo a diccionario"""
        return {
            'user_id': self.user_id,
            'fund_id': self.fund_id,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'active': self.active,
            'subscription_amount': str(self.subscription_amount),
            'invested_amount': str(self.invested_amount),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserNotifications(Model):
    """
    Modelo PynamoDB para representar las preferencias de notificación del usuario
    """
    class Meta:
        table_name = f"{settings.DYNAMODB_TABLE_PREFIX}user_notifications"
        region = settings.AWS_DEFAULT_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    # Clave primaria
    user_id = UnicodeAttribute(hash_key=True)
    
    # Preferencias de notificación
    notification_type = UnicodeAttribute(default='email')  # 'email' o 'sms'
    email_enabled = BooleanAttribute(default=True)
    sms_enabled = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    @classmethod
    def get_or_create_preferences(cls, user_id: str) -> 'UserNotifications':
        """Obtener o crear las preferencias de notificación de un usuario"""
        try:
            return cls.get(user_id)
        except cls.DoesNotExist:
            # Crear preferencias por defecto (email)
            preferences = cls(
                user_id=user_id,
                notification_type='email',
                email_enabled=True,
                sms_enabled=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            preferences.save()
            return preferences
    
    def update_notification_type(self, notification_type: str) -> bool:
        """Actualizar el tipo de notificación preferido"""
        try:
            if notification_type not in ['email', 'sms']:
                return False
            
            self.notification_type = notification_type
            self.email_enabled = (notification_type == 'email')
            self.sms_enabled = (notification_type == 'sms')
            self.updated_at = datetime.utcnow()
            self.save()
            return True
        except Exception:
            return False
    
    def get_preferred_notification_type(self) -> str:
        """Obtener el tipo de notificación preferido del usuario"""
        return self.notification_type
    
    def to_dict(self) -> Dict:
        """Convertir el modelo a diccionario"""
        return {
            'user_id': self.user_id,
            'notification_type': self.notification_type,
            'email_enabled': self.email_enabled,
            'sms_enabled': self.sms_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
