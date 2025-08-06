"""
Serializers para el sistema de gestión de fondos
Contiene todas las validaciones de datos y reglas de negocio
"""

from rest_framework import serializers
from decimal import Decimal
from .models import Fund, UserBalance, UserFund, UserNotifications, User


class FundSerializer(serializers.Serializer):
    """Serializer para mostrar información de fondos"""
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    minimum_amount = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.CharField(read_only=True)


class UserBalanceSerializer(serializers.Serializer):
    """Serializer para mostrar saldo del usuario"""
    user_id = serializers.CharField(read_only=True)
    available_balance = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class UserFundSerializer(serializers.Serializer):
    """Serializer para mostrar suscripciones del usuario"""
    user_id = serializers.CharField(read_only=True)
    fund_id = serializers.CharField(read_only=True)
    subscribed_at = serializers.CharField(read_only=True)
    cancelled_at = serializers.CharField(read_only=True, allow_null=True)
    active = serializers.BooleanField(read_only=True)
    subscription_amount = serializers.CharField(read_only=True)
    invested_amount = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class TransactionSerializer(serializers.Serializer):
    """Serializer para mostrar transacciones"""
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    fund_id = serializers.CharField(read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    amount = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    notification_sent = serializers.BooleanField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class UserSerializer(serializers.Serializer):
    """Serializer para mostrar información del usuario"""
    user_id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    document_number = serializers.CharField(read_only=True)
    document_type = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class NotificationPreferencesSerializer(serializers.Serializer):
    """Serializer para preferencias de notificación"""
    notification_type = serializers.ChoiceField(
        choices=['email', 'sms'],
        help_text="Tipo de notificación preferido: 'email' o 'sms'"
    )

    def validate_notification_type(self, value):
        """Validar que el tipo de notificación sea válido"""
        if value not in ['email', 'sms']:
            raise serializers.ValidationError(
                "El tipo de notificación debe ser 'email' o 'sms'"
            )
        return value


class FundSubscriptionSerializer(serializers.Serializer):
    """
    Serializer para suscripción a fondos con validaciones de negocio
    """
    
    def __init__(self, *args, **kwargs):
        # Extraer fund_id y user del contexto
        self.fund_id = kwargs.pop('fund_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        """Validaciones de negocio para suscripción"""
        if not self.fund_id:
            raise serializers.ValidationError({"fund_id": "ID del fondo es requerido"})
        
        if not self.user:
            raise serializers.ValidationError({"user": "Usuario es requerido"})

        # 1. Verificar que el fondo existe y está activo
        try:
            from .models import Fund
            fund = Fund.get(self.fund_id)
            if not fund.is_active:
                raise serializers.ValidationError({"fund": "El fondo no está disponible"})
        except Exception:
            raise serializers.ValidationError({"fund": "El fondo especificado no existe"})

        # 2. Verificar que el usuario no esté ya suscrito al fondo
        from .models import UserFund
        can_subscribe, error_message = UserFund.can_user_subscribe(
            self.user.user_id, 
            self.fund_id
        )
        
        if not can_subscribe:
            raise serializers.ValidationError({"subscription": error_message})

        # 3. Verificar que el usuario tenga saldo suficiente
        from .models import UserBalance
        from decimal import Decimal
        
        user_balance = UserBalance.get_or_create_balance(self.user.user_id)
        available_balance = Decimal(str(user_balance.available_balance))
        minimum_amount = Decimal(str(fund.minimum_amount))

        if available_balance < minimum_amount:
            raise serializers.ValidationError({
                "balance": f"Saldo insuficiente. Se requieren ${minimum_amount:,.0f} "
                          f"pero solo tiene ${available_balance:,.0f} disponibles"
            })

        # Agregar datos validados al resultado
        attrs.update({
            'fund': fund,
            'user_balance': user_balance,
            'minimum_amount': minimum_amount
        })
        
        return attrs


class FundCancellationSerializer(serializers.Serializer):
    """
    Serializer para cancelación de suscripciones con validaciones de negocio
    """
    
    def __init__(self, *args, **kwargs):
        # Extraer fund_id y user del contexto
        self.fund_id = kwargs.pop('fund_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        """Validaciones de negocio para cancelación"""
        if not self.fund_id:
            raise serializers.ValidationError({"fund_id": "ID del fondo es requerido"})
        
        if not self.user:
            raise serializers.ValidationError({"user": "Usuario es requerido"})

        # 1. Verificar que el fondo existe
        try:
            from .models import Fund
            fund = Fund.get(self.fund_id)
        except Exception:
            raise serializers.ValidationError({"fund": "El fondo especificado no existe"})

        # 2. Verificar que el usuario esté suscrito al fondo
        from .models import UserFund
        subscription = UserFund.get_subscription(self.user.user_id, self.fund_id)
        
        if not subscription:
            raise serializers.ValidationError({
                "subscription": "No tiene una suscripción a este fondo"
            })
        
        if not subscription.active:
            raise serializers.ValidationError({
                "subscription": "La suscripción a este fondo ya está cancelada"
            })

        # 3. Obtener el saldo del usuario para el reembolso
        from .models import UserBalance
        from decimal import Decimal
        
        user_balance = UserBalance.get_or_create_balance(self.user.user_id)

        # Agregar datos validados al resultado
        attrs.update({
            'fund': fund,
            'subscription': subscription,
            'user_balance': user_balance,
            'refund_amount': Decimal(str(subscription.invested_amount))
        })
        
        return attrs


class UserNotificationsSerializer(serializers.Serializer):
    """Serializer para mostrar preferencias de notificación"""
    user_id = serializers.CharField(read_only=True)
    notification_type = serializers.CharField(read_only=True)
    email_enabled = serializers.BooleanField(read_only=True)
    sms_enabled = serializers.BooleanField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)
