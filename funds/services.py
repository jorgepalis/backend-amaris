"""
Servicios de lógica de negocio para el sistema de gestión de fondos
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Importar Twilio solo si está disponible
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio no está instalado. SMS no estará disponible.")

from .models import Fund, UserBalance, Transaction


class FundService:
    """
    Servicio para manejar la lógica de negocio relacionada con los fondos
    """
    
    def get_available_funds(self) -> List[Dict]:
        """Obtener todos los fondos disponibles para suscripción"""
        funds = Fund.get_active_funds()
        return [fund.to_dict() for fund in funds]
    
    def get_fund_details(self, fund_id: str) -> Optional[Dict]:
        """Obtener detalles de un fondo específico"""
        try:
            fund = Fund.get(fund_id)
            return fund.to_dict()
        except Fund.DoesNotExist:
            return None
    
    def subscribe_to_fund(self, user_id: str, fund_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Suscribir un usuario a un fondo
        
        Returns:
            Tuple[success, message, transaction_data]
        """
        # 1. Verificar que el fondo existe
        try:
            fund = Fund.get(fund_id)
        except Fund.DoesNotExist:
            return False, "El fondo especificado no existe", None
        
        if not fund.is_active:
            return False, "El fondo no está disponible para suscripciones", None
        
        # 2. Obtener o crear el saldo del usuario
        user_balance = UserBalance.get_or_create_balance(user_id)
        current_balance = Decimal(str(user_balance.available_balance))
        minimum_amount = Decimal(str(fund.minimum_amount))
        
        # 3. Verificar saldo suficiente
        if current_balance < minimum_amount:
            return False, f"No tiene saldo disponible para vincularse al fondo {fund.name}", None
        
        # 4. Crear la transacción
        transaction = Transaction.create_transaction(
            user_id=user_id,
            fund_id=fund_id,
            transaction_type='SUBSCRIPTION',
            amount=minimum_amount,
            status='PENDING'
        )
        transaction.save()
        
        # 5. Actualizar el saldo del usuario
        new_balance = current_balance - minimum_amount
        balance_updated = user_balance.update_balance(new_balance)
        
        if balance_updated:
            # 6. Marcar la transacción como completada
            transaction.update_status('COMPLETED')
            
            return True, f"Suscripción exitosa al fondo {fund.name}", transaction.to_dict()
        else:
            # 7. Si falla la actualización del saldo, marcar transacción como fallida
            transaction.update_status('FAILED')
            return False, "Error procesando la transacción", None
    
    def cancel_fund_subscription(self, user_id: str, fund_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Cancelar la suscripción de un usuario a un fondo
        
        Returns:
            Tuple[success, message, transaction_data]
        """
        # 1. Verificar que el fondo existe
        try:
            fund = Fund.get(fund_id)
        except Fund.DoesNotExist:
            return False, "El fondo especificado no existe", None
        
        # 2. Buscar la última suscripción activa del usuario a este fondo
        user_transactions = Transaction.get_user_transactions(user_id, limit=50)
        
        # Buscar la última suscripción completada a este fondo sin cancelar
        last_subscription = None
        for transaction in user_transactions:
            if (transaction.fund_id == fund_id and 
                transaction.transaction_type == 'SUBSCRIPTION' and 
                transaction.status == 'COMPLETED'):
                
                # Verificar si ya fue cancelada
                already_cancelled = any(
                    t.fund_id == fund_id and 
                    t.transaction_type == 'CANCELLATION' and 
                    t.status == 'COMPLETED' and
                    t.created_at > transaction.created_at
                    for t in user_transactions
                )
                
                if not already_cancelled:
                    last_subscription = transaction
                    break
        
        if not last_subscription:
            return False, f"No tiene una suscripción activa al fondo {fund.name}", None
        
        # 3. Obtener el saldo actual del usuario
        user_balance = UserBalance.get_or_create_balance(user_id)
        current_balance = Decimal(str(user_balance.available_balance))
        refund_amount = Decimal(str(last_subscription.amount))
        
        # 4. Crear la transacción de cancelación
        transaction = Transaction.create_transaction(
            user_id=user_id,
            fund_id=fund_id,
            transaction_type='CANCELLATION',
            amount=refund_amount,
            status='PENDING'
        )
        transaction.save()
        
        # 5. Devolver el dinero al usuario
        new_balance = current_balance + refund_amount
        balance_updated = user_balance.update_balance(new_balance)
        
        if balance_updated:
            # 6. Marcar la transacción como completada
            transaction.update_status('COMPLETED')
            
            return True, f"Cancelación exitosa del fondo {fund.name}", transaction.to_dict()
        else:
            # 7. Si falla la actualización del saldo, marcar transacción como fallida
            transaction.update_status('FAILED')
            return False, "Error procesando la cancelación", None
    
    def get_user_balance(self, user_id: str) -> Dict:
        """Obtener el saldo actual del usuario"""
        user_balance = UserBalance.get_or_create_balance(user_id)
        
        return {
            'user_id': user_id,
            'available_balance': Decimal(str(user_balance.available_balance)),
            'formatted_balance': f"COP ${user_balance.available_balance:,.2f}"
        }
    
    def get_user_transaction_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Obtener el historial de transacciones del usuario"""
        transactions = Transaction.get_user_transactions(user_id, limit)
        
        # Enriquecer las transacciones con información del fondo
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
                'formatted_amount': f"COP ${float(transaction.amount):,.2f}",
                'transaction_type_display': 'Suscripción' if transaction.transaction_type == 'SUBSCRIPTION' else 'Cancelación'
            })
            enriched_transactions.append(transaction_data)
        
        return enriched_transactions


class NotificationService:
    """
    Servicio para manejar notificaciones (email/SMS) con implementaciones reales
    """
    
    def __init__(self):
        """Inicializar el servicio de notificaciones"""
        self.notifications_enabled = getattr(settings, 'NOTIFICATIONS_ENABLED', True)
        self.notification_mode = getattr(settings, 'NOTIFICATION_MODE', 'development')
        
        # Configurar Twilio si está disponible
        if TWILIO_AVAILABLE and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.twilio_client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.twilio_phone = settings.TWILIO_PHONE_NUMBER
            self.twilio_messaging_service_sid = getattr(settings, 'TWILIO_MESSAGING_SERVICE_SID', None)
        else:
            self.twilio_client = None
            self.twilio_phone = None
            self.twilio_messaging_service_sid = None
    
    def send_transaction_notification(self, user, transaction: Dict, notification_type: str = 'email') -> bool:
        """
        Enviar notificación de transacción
        
        Args:
            user: Objeto User con información del usuario
            transaction: Datos de la transacción
            notification_type: 'email' o 'sms'
        """
        if not self.notifications_enabled:
            logger.info(f"Notificaciones deshabilitadas. No se envía notificación a {user.name}")
            return True
        
        try:
            if notification_type == 'email':
                return self._send_email_notification(user, transaction)
            elif notification_type == 'sms':
                return self._send_sms_notification(user, transaction)
            else:
                logger.error(f"Tipo de notificación no válido: {notification_type}")
                return False
        except Exception as e:
            logger.error(f"Error enviando notificación {notification_type} a {user.name}: {str(e)}")
            return False
    
    def _send_email_notification(self, user, transaction: Dict) -> bool:
        """Enviar notificación por email"""
        try:
            # Preparar datos para el template
            context = {
                'user_name': user.name,
                'transaction': transaction,
                'transaction_type_display': 'Suscripción' if transaction['transaction_type'] == 'SUBSCRIPTION' else 'Cancelación',
                'formatted_amount': f"COP ${float(transaction['amount']):,.2f}",
                'company_name': 'El Cliente - Gestión de Fondos'
            }
            
            # Crear el mensaje
            subject = f"Confirmación de {context['transaction_type_display']} - Gestión de Fondos"
            
            # Mensaje en texto plano
            message = self._build_email_message(context)
            
            # Mensaje HTML (opcional)
            html_message = self._build_html_email_message(context)
            
            if self.notification_mode == 'development':
                # En modo desarrollo, solo mostrar en consola
                print(f"\n📧 EMAIL ENVIADO A: {user.name} ({user.email})")
                print(f"📧 ASUNTO: {subject}")
                print(f"📧 MENSAJE:\n{message}")
                return True
            else:
                # En modo producción, enviar email real
                result = send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False
                )
                
                logger.info(f"Email enviado exitosamente a {user.email}")
                return result == 1
                
        except Exception as e:
            logger.error(f"Error enviando email a {user.email}: {str(e)}")
            return False
    
    def _send_sms_notification(self, user, transaction: Dict) -> bool:
        """Enviar notificación por SMS"""
        try:
            # Crear mensaje SMS (más corto que email)
            message = self._build_sms_message(user, transaction)
            
            if self.notification_mode == 'development':
                # En modo desarrollo, solo mostrar en consola
                print(f"\n📱 SMS ENVIADO A: {user.name} ({user.phone})")
                print(f"📱 MENSAJE: {message}")
                return True
            else:
                # En modo producción, enviar SMS real
                if not self.twilio_client:
                    logger.error("Twilio no está configurado. No se puede enviar SMS.")
                    return False
                
                # Debug: mostrar configuración
                logger.info(f"🔧 Twilio Account SID: {settings.TWILIO_ACCOUNT_SID[:10]}...")
                logger.info(f"🔧 Messaging Service SID: {self.twilio_messaging_service_sid}")
                logger.info(f"🔧 Phone number: {self.twilio_phone}")
                
                # Usar Messaging Service si está disponible, sino usar número telefónico
                if self.twilio_messaging_service_sid:
                    logger.info("📱 Enviando SMS usando Messaging Service...")
                    message_instance = self.twilio_client.messages.create(
                        body=message,
                        messaging_service_sid=self.twilio_messaging_service_sid,
                        to=user.phone
                    )
                else:
                    logger.info("📱 Enviando SMS usando número telefónico...")
                    message_instance = self.twilio_client.messages.create(
                        body=message,
                        from_=self.twilio_phone,
                        to=user.phone
                    )
                
                logger.info(f"SMS enviado exitosamente a {user.phone}. SID: {message_instance.sid}")
                return True
                return True
                
        except Exception as e:
            logger.error(f"Error enviando SMS a {user.phone}: {str(e)}")
            return False
    
    def _build_email_message(self, context: Dict) -> str:
        """Construir mensaje de email en texto plano"""
        return f"""
Estimado/a {context['user_name']},

Su {context['transaction_type_display'].lower()} ha sido procesada exitosamente.

DETALLES DE LA TRANSACCIÓN:
• ID: {context['transaction']['id']}
• Tipo: {context['transaction_type_display']}
• Monto: {context['formatted_amount']}
• Estado: {context['transaction']['status']}
• Fecha: {context['transaction']['created_at']}

{self._get_transaction_specific_message(context['transaction'])}

Si tiene alguna pregunta, no dude en contactarnos.

Atentamente,
{context['company_name']}

---
Este es un mensaje automático, por favor no responda a este email.
        """.strip()
    
    def _build_html_email_message(self, context: Dict) -> str:
        """Construir mensaje de email en HTML"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #2c3e50;">Confirmación de {context['transaction_type_display']}</h2>
                
                <p>Estimado/a <strong>{context['user_name']}</strong>,</p>
                
                <p>Su {context['transaction_type_display'].lower()} ha sido procesada exitosamente.</p>
                
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #34495e; margin-top: 0;">Detalles de la Transacción</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li><strong>ID:</strong> {context['transaction']['id']}</li>
                        <li><strong>Tipo:</strong> {context['transaction_type_display']}</li>
                        <li><strong>Monto:</strong> {context['formatted_amount']}</li>
                        <li><strong>Estado:</strong> {context['transaction']['status']}</li>
                        <li><strong>Fecha:</strong> {context['transaction']['created_at']}</li>
                    </ul>
                </div>
                
                <p>{self._get_transaction_specific_message(context['transaction'])}</p>
                
                <p>Si tiene alguna pregunta, no dude en contactarnos.</p>
                
                <p style="margin-top: 30px;">
                    Atentamente,<br>
                    <strong>{context['company_name']}</strong>
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #6c757d; font-size: 12px;">
                    Este es un mensaje automático, por favor no responda a este email.
                </p>
            </div>
        </body>
        </html>
        """.strip()
    
    def _build_sms_message(self, user, transaction: Dict) -> str:
        """Construir mensaje SMS (limitado a 160 caracteres)"""
        transaction_type = "suscripción" if transaction['transaction_type'] == 'SUBSCRIPTION' else "cancelación"
        amount = f"COP ${float(transaction['amount']):,.0f}"
        
        return f"Hola {user.name}! Su {transaction_type} por {amount} fue procesada exitosamente. ID: {transaction['id'][:8]}... - El Cliente"
    
    def _get_transaction_specific_message(self, transaction: Dict) -> str:
        """Obtener mensaje específico según el tipo de transacción"""
        if transaction['transaction_type'] == 'SUBSCRIPTION':
            return "¡Bienvenido/a a nuestro fondo de inversión! Su dinero ha sido invertido exitosamente."
        else:
            return "Su cancelación ha sido procesada y el dinero ha sido devuelto a su saldo disponible."
