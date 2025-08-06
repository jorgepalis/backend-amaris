"""
Views/APIs para el sistema de gestión de fondos
Refactorizadas para usar serializers con validaciones
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from django.http import JsonResponse
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.openapi import OpenApiTypes
from .models import Fund, UserBalance, Transaction, User, UserFund, UserNotifications
from .services import NotificationService
from .serializers import (
    NotificationPreferencesSerializer,
    FundSubscriptionSerializer, FundCancellationSerializer
)

# Como la prueba técnica dice "usuario único", usamos el usuario por defecto
def get_current_user():
    """Obtener el usuario actual del sistema (usuario único según la prueba)"""
    return User.get_default_user()


@extend_schema(
    summary="Listar fondos disponibles",
    description="Obtiene una lista de todos los fondos de inversión activos disponibles para suscripción",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "minimum_amount": {"type": "string"},
                            "category": {"type": "string"},
                            "is_active": {"type": "boolean"}
                        }
                    }
                },
                "message": {"type": "string"}
            }
        }
    },
    tags=["Fondos"]
)
class FundListView(APIView):
    """
    GET /api/funds/
    Listar todos los fondos disponibles
    """
    
    def get(self, request):
        """Obtener lista de fondos activos"""
        try:
            funds = Fund.get_active_funds()
            funds_data = [fund.to_dict() for fund in funds]
            
            return Response({
                'success': True,
                'data': funds_data,
                'message': f'Se encontraron {len(funds_data)} fondos disponibles'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo la lista de fondos'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Suscribirse a un fondo de inversión",
    description="Permite al usuario suscribirse a un fondo específico con validaciones automáticas de saldo y duplicados",
    responses={
        201: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "transaction_id": {"type": "string"},
                        "user_name": {"type": "string"},
                        "fund_name": {"type": "string"},
                        "amount": {"type": "string"},
                        "new_balance": {"type": "string"},
                        "notification_sent": {"type": "boolean"},
                        "notification_type": {"type": "string"}
                    }
                },
                "message": {"type": "string"}
            }
        },
        400: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "error": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    },
    tags=["Fondos"]
)
class FundSubscribeView(APIView):
    """
    POST /api/funds/{fund_id}/subscribe/
    Suscribirse a un fondo con validaciones en el serializer
    """
    
    def post(self, request, fund_id):
        """Suscribirse a un fondo usando serializer con todas las validaciones"""
        try:
            # 1. Obtener usuario del sistema
            user = get_current_user()
            
            # 2. Obtener preferencias de notificación
            preferences = UserNotifications.get_or_create_preferences(user.user_id)
            notification_type = preferences.get_preferred_notification_type()
            
            # 3. Validar usando serializer con las reglas de negocio
            serializer = FundSubscriptionSerializer(
                data={}, 
                fund_id=fund_id, 
                user=user
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors,
                    'message': 'Falló la validación de suscripción'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. Extraer datos validados del serializer
            validated_data = serializer.validated_data
            fund = validated_data['fund']
            user_balance = validated_data['user_balance']
            minimum_amount = validated_data['minimum_amount']
            current_balance = Decimal(str(user_balance.available_balance))
            
            # 5. Crear transacción
            transaction = Transaction.create_transaction(
                user_id=user.user_id,
                fund_id=fund_id,
                transaction_type='SUBSCRIPTION',
                amount=minimum_amount,
                status='PENDING'
            )
            transaction.save()
            
            # 6. Actualizar saldo del usuario
            new_balance = current_balance - minimum_amount
            balance_updated = user_balance.update_balance(new_balance)
            
            if balance_updated:
                # 7. Marcar transacción como completada
                transaction.update_status('COMPLETED')
                
                # 8. Crear/actualizar suscripción en UserFund
                try:
                    user_fund = UserFund.get_subscription(user.user_id, fund_id)
                    if user_fund:
                        # Reactivar suscripción existente
                        if not user_fund.active:
                            user_fund.reactivate_subscription()
                            user_fund.subscription_amount = float(minimum_amount)
                            user_fund.invested_amount = float(minimum_amount)
                            user_fund.subscribed_at = datetime.utcnow()
                            user_fund.save()
                    else:
                        # Crear nueva suscripción
                        user_fund = UserFund.create_subscription(
                            user.user_id, fund_id, minimum_amount, minimum_amount
                        )
                        user_fund.save()
                except Exception as e:
                    print(f"Error creando suscripción UserFund: {e}")
                
                # 9. Enviar notificación
                notification_service = NotificationService()
                notification_sent = notification_service.send_transaction_notification(
                    user, transaction.to_dict(), notification_type
                )
                
                if notification_sent:
                    transaction.notification_sent = True
                    transaction.save()
                
                return Response({
                    'success': True,
                    'message': f'Suscripción exitosa al fondo {fund.name}',
                    'data': {
                        'transaction_id': transaction.id,
                        'user_name': user.name,
                        'user_email': user.email,
                        'fund_name': fund.name,
                        'amount': str(minimum_amount),
                        'new_balance': str(new_balance),
                        'notification_sent': notification_sent,
                        'notification_type': notification_type,
                        'notification_contact': user.email if notification_type == 'email' else user.phone
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                # Si falla la actualización del saldo, marcar transacción como fallida
                transaction.update_status('FAILED')
                return Response({
                    'success': False,
                    'error': 'Transaction failed',
                    'message': 'Error procesando la transacción'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error interno del servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(
    summary="Obtener detalles de un fondo específico",
    description="Consulta la información completa de un fondo de inversión por su ID",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "minimum_amount": {"type": "string"},
                        "category": {"type": "string"},
                        "is_active": {"type": "boolean"}
                    }
                },
                "message": {"type": "string"}
            }
        },
        404: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "error": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    },
    tags=["Fondos"]
)
class FundDetailView(APIView):
    """
    GET /api/funds/{fund_id}/
    Obtener detalles de un fondo específico
    """
    
    def get(self, request, fund_id):
        """Obtener detalles de un fondo"""
        try:
            fund = Fund.get(fund_id)
            return Response({
                'success': True,
                'data': fund.to_dict(),
                'message': 'Fondo encontrado exitosamente'
            }, status=status.HTTP_200_OK)
            
        except Fund.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Fund not found',
                'message': 'El fondo especificado no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo los detalles del fondo'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Cancelar suscripción a un fondo",
    description="Permite al usuario cancelar su suscripción activa a un fondo con reembolso automático",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "transaction_id": {"type": "string"},
                        "fund_name": {"type": "string"},
                        "refund_amount": {"type": "string"},
                        "new_balance": {"type": "string"},
                        "notification_sent": {"type": "boolean"}
                    }
                },
                "message": {"type": "string"}
            }
        },
        400: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "error": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    },
    tags=["Fondos"]
)
class FundCancellationView(APIView):
    """
    POST /api/funds/{fund_id}/cancel/
    Cancelar suscripción a un fondo usando serializer con validaciones
    """
    
    def post(self, request, fund_id):
        """Cancelar suscripción usando serializer con validaciones"""
        try:
            # 1. Obtener usuario del sistema
            user = get_current_user()
            
            # 2. Obtener preferencias de notificación
            preferences = UserNotifications.get_or_create_preferences(user.user_id)
            notification_type = preferences.get_preferred_notification_type()
            
            # 3. Validar usando serializer con las reglas de negocio
            serializer = FundCancellationSerializer(
                data={}, 
                fund_id=fund_id, 
                user=user
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors,
                    'message': 'Falló la validación de cancelación'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 4. Extraer datos validados del serializer
            validated_data = serializer.validated_data
            fund = validated_data['fund']
            subscription = validated_data['subscription']
            user_balance = validated_data['user_balance']
            refund_amount = validated_data['refund_amount']
            current_balance = Decimal(str(user_balance.available_balance))
            
            # 5. Crear transacción de cancelación
            transaction = Transaction.create_transaction(
                user_id=user.user_id,
                fund_id=fund_id,
                transaction_type='CANCELLATION',
                amount=refund_amount,
                status='PENDING'
            )
            transaction.save()
            
            # 6. Devolver dinero al usuario
            new_balance = current_balance + refund_amount
            balance_updated = user_balance.update_balance(new_balance)
            
            if balance_updated:
                # 7. Marcar transacción como completada
                transaction.update_status('COMPLETED')
                
                # 8. Cancelar suscripción en UserFund
                try:
                    subscription.cancel_subscription()
                except Exception as e:
                    print(f"Error cancelando suscripción UserFund: {e}")
                
                # 9. Enviar notificación
                notification_service = NotificationService()
                notification_sent = notification_service.send_transaction_notification(
                    user, transaction.to_dict(), notification_type
                )
                
                if notification_sent:
                    transaction.notification_sent = True
                    transaction.save()
                
                return Response({
                    'success': True,
                    'message': f'Cancelación exitosa del fondo {fund.name}',
                    'data': {
                        'transaction_id': transaction.id,
                        'fund_name': fund.name,
                        'refund_amount': str(refund_amount),
                        'new_balance': str(new_balance),
                        'notification_sent': notification_sent,
                        'notification_type': notification_type
                    }
                }, status=status.HTTP_200_OK)
            else:
                # Si falla la actualización del saldo, marcar transacción como fallida
                transaction.update_status('FAILED')
                return Response({
                    'success': False,
                    'error': 'Cancellation failed',
                    'message': 'Error procesando la cancelación'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error interno del servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Obtener saldo del usuario",
    description="Consulta el saldo disponible del usuario único del sistema",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "available_balance": {"type": "string"},
                        "formatted_balance": {"type": "string"},
                        "updated_at": {"type": "string"}
                    }
                },
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class UserBalanceView(APIView):
    """
    GET /api/user/balance/
    Obtener saldo actual del usuario
    """
    
    def get(self, request):
        """Obtener saldo actual del usuario"""
        # Obtener el usuario actual del sistema
        user = get_current_user()
        user_id = user.user_id
        
        try:
            user_balance = UserBalance.get_or_create_balance(user_id)
            
            return Response({
                'success': True,
                'data': {
                    'user_id': user_id,
                    'available_balance': str(user_balance.available_balance),
                    'formatted_balance': f'COP ${user_balance.available_balance:,.2f}',
                    'updated_at': user_balance.updated_at.isoformat() if user_balance.updated_at else None
                },
                'message': 'Saldo obtenido exitosamente'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo el saldo del usuario'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Obtener historial de transacciones del usuario",
    description="Consulta el historial completo de transacciones (suscripciones y cancelaciones) del usuario",
    parameters=[
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Número máximo de transacciones a retornar (por defecto: 10)'
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "fund_id": {"type": "string"},
                            "fund_name": {"type": "string"},
                            "transaction_type": {"type": "string"},
                            "transaction_type_display": {"type": "string"},
                            "amount": {"type": "string"},
                            "formatted_amount": {"type": "string"},
                            "status": {"type": "string"},
                            "created_at": {"type": "string"},
                            "notification_sent": {"type": "boolean"}
                        }
                    }
                },
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class TransactionHistoryView(APIView):
    """
    GET /api/user/transactions/
    Obtener historial de transacciones del usuario
    """
    
    def get(self, request):
        """Obtener historial de transacciones"""
        # Obtener el usuario actual del sistema
        user = get_current_user()
        user_id = user.user_id
        limit = int(request.query_params.get('limit', 10))
        
        try:
            transactions = Transaction.get_user_transactions(user_id, limit)
            
            # Enriquecer con información del fondo
            enriched_transactions = []
            for transaction in transactions:
                try:
                    fund = Fund.get(transaction.fund_id)
                    fund_name = fund.name
                except Fund.DoesNotExist:
                    fund_name = 'Fondo no encontrado'
                
                transaction_data = transaction.to_dict()
                transaction_data.update({
                    'fund_name': fund_name,
                    'formatted_amount': f'COP ${float(transaction.amount):,.2f}',
                    'transaction_type_display': 'Suscripción' if transaction.transaction_type == 'SUBSCRIPTION' else 'Cancelación'
                })
                enriched_transactions.append(transaction_data)
            
            return Response({
                'success': True,
                'data': enriched_transactions,
                'message': f'Se encontraron {len(enriched_transactions)} transacciones'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo el historial de transacciones'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Obtener información del usuario actual",
    description="Obtiene la información completa del usuario actual del sistema",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "document_number": {"type": "string"},
                        "document_type": {"type": "string"},
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"}
                    }
                },
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class UserInfoView(APIView):
    """
    GET /api/user/info/
    Obtener información del usuario actual
    """
    
    def get(self, request):
        """Obtener información del usuario actual"""
        try:
            user = get_current_user()
            
            return Response({
                'success': True,
                'data': user.to_dict(),
                'message': 'Información del usuario obtenida exitosamente'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo la información del usuario'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Obtener información del usuario actual",
    description="Obtiene toda la información del usuario único del sistema",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "document_number": {"type": "string"},
                        "document_type": {"type": "string"},
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"}
                    }
                },
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class UserDetailView(APIView):
    """
    GET /api/user/
    Obtener información del usuario actual
    """
    
    def get(self, request):
        """Obtener información completa del usuario actual"""
        try:
            # Obtener el usuario actual del sistema
            user = get_current_user()
            
            return Response({
                'success': True,
                'data': user.to_dict(),
                'message': f'Información del usuario {user.name}'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo la información del usuario'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Obtener fondos activos del usuario",
    description="Obtiene todos los fondos a los que el usuario está suscrito actualmente",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subscription": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string"},
                                    "fund_id": {"type": "string"},
                                    "subscribed_at": {"type": "string"},
                                    "active": {"type": "boolean"},
                                    "subscription_amount": {"type": "string"}
                                }
                            },
                            "fund": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "minimum_amount": {"type": "string"},
                                    "category": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class UserActiveFundsView(APIView):
    """
    GET /api/user/funds/
    Obtener fondos activos del usuario
    """
    
    def get(self, request):
        """Obtener todos los fondos a los que el usuario está suscrito"""
        try:
            # Obtener el usuario actual del sistema
            user = get_current_user()
            user_id = user.user_id
            
            # Obtener suscripciones activas del usuario
            active_subscriptions = UserFund.get_user_active_funds(user_id)
            
            # Enriquecer con información de los fondos
            enriched_funds = []
            for subscription in active_subscriptions:
                try:
                    fund = Fund.get(subscription.fund_id)
                    enriched_funds.append({
                        'subscription': subscription.to_dict(),
                        'fund': fund.to_dict()
                    })
                except Fund.DoesNotExist:
                    # Si el fondo no existe, marcar la suscripción como inactiva
                    subscription.cancel_subscription()
            
            return Response({
                'success': True,
                'data': enriched_funds,
                'message': f'Se encontraron {len(enriched_funds)} fondos activos'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo los fondos activos del usuario'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Obtener preferencias de notificación del usuario",
    description="Obtiene las preferencias de notificación configuradas para el usuario actual",
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "notification_type": {
                            "type": "string", 
                            "enum": ["email", "sms"],
                            "description": "Tipo de notificación preferido actualmente"
                        },
                        "email_enabled": {"type": "boolean"},
                        "sms_enabled": {"type": "boolean"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"}
                    }
                },
                "message": {"type": "string"}
            },
            "example": {
                "success": True,
                "data": {
                    "user_id": "user_default",
                    "notification_type": "email",
                    "email_enabled": True,
                    "sms_enabled": False,
                    "created_at": "2025-08-04T10:30:00Z",
                    "updated_at": "2025-08-04T10:30:00Z"
                },
                "message": "Preferencias de notificación: email"
            }
        },
        500: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "error": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class UserNotificationPreferencesView(APIView):
    """
    GET /api/user/notifications/
    Obtener preferencias de notificación del usuario
    """
    
    def get(self, request):
        """Obtener preferencias de notificación del usuario"""
        try:
            user = get_current_user()
            preferences = UserNotifications.get_or_create_preferences(user.user_id)
            
            return Response({
                'success': True,
                'data': preferences.to_dict(),
                'message': f'Preferencias de notificación: {preferences.notification_type}'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error obteniendo las preferencias de notificación'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Actualizar preferencias de notificación del usuario",
    description="Permite al usuario cambiar su método preferido de notificación entre email y SMS",
    request=NotificationPreferencesSerializer,
    examples=[
        OpenApiExample(
            'Cambiar a SMS',
            summary='Configurar notificaciones por SMS',
            description='Cambiar las preferencias del usuario para recibir notificaciones por SMS',
            value={
                "notification_type": "sms"
            },
            request_only=True,
        ),
        OpenApiExample(
            'Cambiar a Email',
            summary='Configurar notificaciones por Email',
            description='Cambiar las preferencias del usuario para recibir notificaciones por email',
            value={
                "notification_type": "email"
            },
            request_only=True,
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "notification_type": {"type": "string"},
                        "email_enabled": {"type": "boolean"},
                        "sms_enabled": {"type": "boolean"},
                        "updated_at": {"type": "string"}
                    }
                },
                "message": {"type": "string"}
            }
        },
        400: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "error": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    },
    tags=["Usuario"]
)
class UpdateNotificationPreferencesView(APIView):
    """
    PUT /api/user/notifications/
    Actualizar preferencias de notificación del usuario
    """
    
    def put(self, request):
        """Actualizar preferencias de notificación usando serializer"""
        try:
            user = get_current_user()
            
            # Validar usando el serializer
            serializer = NotificationPreferencesSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Invalid data',
                    'details': serializer.errors,
                    'message': 'Datos inválidos. El tipo de notificación debe ser "email" o "sms"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener el valor validado
            notification_type = serializer.validated_data['notification_type']
            
            preferences = UserNotifications.get_or_create_preferences(user.user_id)
            updated = preferences.update_notification_type(notification_type)
            
            if updated:
                return Response({
                    'success': True,
                    'data': preferences.to_dict(),
                    'message': f'Preferencias actualizadas a: {notification_type}'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Update failed',
                    'message': 'Error actualizando las preferencias'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error interno del servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)