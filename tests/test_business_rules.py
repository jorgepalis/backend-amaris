"""
Pruebas de integración para las reglas de negocio del sistema de gestión de fondos
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from datetime import datetime

from funds.services import FundService
from funds.models import Fund, UserBalance, Transaction, User


class TestFundSubscriptionBusinessRules:
    """
    Pruebas para las reglas de negocio de suscripción a fondos
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "test_user_123"
        self.test_fund_id = "test_fund_456"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    def test_successful_fund_subscription(self, mock_transaction, mock_balance, mock_fund):
        """
        Prueba: Suscripción exitosa a un fondo cuando el usuario tiene saldo suficiente
        
        Regla de negocio: Un usuario puede suscribirse a un fondo si:
        - El fondo existe y está activo
        - El usuario tiene saldo suficiente (>= monto mínimo)
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 500000  # Usuario tiene 500k disponible
        mock_balance_obj.update_balance.return_value = True
        mock_balance.return_value = mock_balance_obj
        
        mock_transaction_obj = Mock()
        mock_transaction_obj.to_dict.return_value = {
            'id': 'txn_123',
            'user_id': self.test_user_id,
            'fund_id': self.test_fund_id,
            'amount': 125000,
            'transaction_type': 'SUBSCRIPTION',
            'status': 'COMPLETED'
        }
        mock_transaction_obj.save = Mock()
        mock_transaction_obj.update_status = Mock()
        mock_transaction.return_value = mock_transaction_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is True
        assert "Suscripción exitosa" in message
        assert transaction_data is not None
        assert transaction_data['transaction_type'] == 'SUBSCRIPTION'
        
        # Verificar que se llamaron los métodos correctos
        mock_fund.assert_called_once_with(self.test_fund_id)
        mock_balance.assert_called_once_with(self.test_user_id)
        mock_balance_obj.update_balance.assert_called_once_with(Decimal('375000'))  # 500k - 125k
        mock_transaction_obj.update_status.assert_called_once_with('COMPLETED')
    
    @patch('funds.models.Fund.get')
    def test_subscription_fails_when_fund_not_exists(self, mock_fund):
        """
        Prueba: La suscripción falla cuando el fondo no existe
        
        Regla de negocio: No se puede suscribir a un fondo inexistente
        """
        # Arrange
        mock_fund.side_effect = Fund.DoesNotExist()
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, 
            "fondo_inexistente"
        )
        
        # Assert
        assert success is False
        assert "El fondo especificado no existe" in message
        assert transaction_data is None
    
    @patch('funds.models.Fund.get')
    def test_subscription_fails_when_fund_inactive(self, mock_fund):
        """
        Prueba: La suscripción falla cuando el fondo está inactivo
        
        Regla de negocio: No se puede suscribir a un fondo inactivo
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.is_active = False
        mock_fund.return_value = mock_fund_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "El fondo no está disponible" in message
        assert transaction_data is None
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    def test_subscription_fails_insufficient_balance(self, mock_balance, mock_fund):
        """
        Prueba: La suscripción falla cuando el usuario no tiene saldo suficiente
        
        Regla de negocio: El saldo disponible debe ser >= monto mínimo del fondo
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 50000  # Solo tiene 50k, necesita 125k
        mock_balance.return_value = mock_balance_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "No tiene saldo disponible" in message
        assert transaction_data is None
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    def test_subscription_fails_when_balance_update_fails(self, mock_transaction, mock_balance, mock_fund):
        """
        Prueba: La suscripción falla si no se puede actualizar el saldo del usuario
        
        Regla de negocio: Si la actualización del saldo falla, la transacción debe marcarse como fallida
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 500000
        mock_balance_obj.update_balance.return_value = False  # Falla la actualización
        mock_balance.return_value = mock_balance_obj
        
        mock_transaction_obj = Mock()
        mock_transaction_obj.save = Mock()
        mock_transaction_obj.update_status = Mock()
        mock_transaction.return_value = mock_transaction_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "Error procesando la transacción" in message
        assert transaction_data is None
        mock_transaction_obj.update_status.assert_called_once_with('FAILED')


class TestFundCancellationBusinessRules:
    """
    Pruebas para las reglas de negocio de cancelación de suscripciones
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "test_user_123"
        self.test_fund_id = "test_fund_456"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.Transaction.get_user_transactions')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    def test_successful_fund_cancellation(self, mock_transaction, mock_balance, mock_user_transactions, mock_fund):
        """
        Prueba: Cancelación exitosa de una suscripción activa
        
        Regla de negocio: Un usuario puede cancelar una suscripción si:
        - El fondo existe
        - Tiene una suscripción activa al fondo (no cancelada previamente)
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund.return_value = mock_fund_obj
        
        # Simular una suscripción activa
        mock_subscription = Mock()
        mock_subscription.fund_id = self.test_fund_id
        mock_subscription.transaction_type = 'SUBSCRIPTION'
        mock_subscription.status = 'COMPLETED'
        mock_subscription.amount = 125000
        mock_subscription.created_at = datetime(2023, 1, 1)
        
        mock_user_transactions.return_value = [mock_subscription]
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 100000
        mock_balance_obj.update_balance.return_value = True
        mock_balance.return_value = mock_balance_obj
        
        mock_transaction_obj = Mock()
        mock_transaction_obj.to_dict.return_value = {
            'id': 'txn_cancel_123',
            'user_id': self.test_user_id,
            'fund_id': self.test_fund_id,
            'amount': 125000,
            'transaction_type': 'CANCELLATION',
            'status': 'COMPLETED'
        }
        mock_transaction_obj.save = Mock()
        mock_transaction_obj.update_status = Mock()
        mock_transaction.return_value = mock_transaction_obj
        
        # Act
        success, message, transaction_data = self.fund_service.cancel_fund_subscription(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is True
        assert "Cancelación exitosa" in message
        assert transaction_data is not None
        assert transaction_data['transaction_type'] == 'CANCELLATION'
        
        # Verificar que se devolvió el dinero
        mock_balance_obj.update_balance.assert_called_once_with(Decimal('225000'))  # 100k + 125k
        mock_transaction_obj.update_status.assert_called_once_with('COMPLETED')
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.Transaction.get_user_transactions')
    def test_cancellation_fails_no_active_subscription(self, mock_user_transactions, mock_fund):
        """
        Prueba: La cancelación falla cuando no hay suscripción activa
        
        Regla de negocio: No se puede cancelar una suscripción inexistente o ya cancelada
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund.return_value = mock_fund_obj
        
        # No hay transacciones
        mock_user_transactions.return_value = []
        
        # Act
        success, message, transaction_data = self.fund_service.cancel_fund_subscription(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "No tiene una suscripción activa" in message
        assert transaction_data is None
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.Transaction.get_user_transactions')
    def test_cancellation_fails_already_cancelled(self, mock_user_transactions, mock_fund):
        """
        Prueba: La cancelación falla cuando la suscripción ya fue cancelada
        
        Regla de negocio: No se puede cancelar dos veces la misma suscripción
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund.return_value = mock_fund_obj
        
        # Simular suscripción y su cancelación posterior
        mock_subscription = Mock()
        mock_subscription.fund_id = self.test_fund_id
        mock_subscription.transaction_type = 'SUBSCRIPTION'
        mock_subscription.status = 'COMPLETED'
        mock_subscription.created_at = datetime(2023, 1, 1)
        
        mock_cancellation = Mock()
        mock_cancellation.fund_id = self.test_fund_id
        mock_cancellation.transaction_type = 'CANCELLATION'
        mock_cancellation.status = 'COMPLETED'
        mock_cancellation.created_at = datetime(2023, 1, 2)  # Posterior a la suscripción
        
        mock_user_transactions.return_value = [mock_cancellation, mock_subscription]
        
        # Act
        success, message, transaction_data = self.fund_service.cancel_fund_subscription(
            self.test_user_id, 
            self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "No tiene una suscripción activa" in message
        assert transaction_data is None


class TestUserBalanceBusinessRules:
    """
    Pruebas para las reglas de negocio del saldo de usuario
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "test_user_123"
    
    @patch('funds.models.UserBalance.get_or_create_balance')
    def test_get_user_balance(self, mock_balance):
        """
        Prueba: Obtener el saldo del usuario correctamente formateado
        
        Regla de negocio: El saldo debe retornarse en formato COP con separadores de miles
        """
        # Arrange
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 1250000.50
        mock_balance.return_value = mock_balance_obj
        
        # Act
        result = self.fund_service.get_user_balance(self.test_user_id)
        
        # Assert
        assert result['user_id'] == self.test_user_id
        assert result['available_balance'] == Decimal('1250000.50')
        assert 'COP $' in result['formatted_balance']
        assert '1,250,000.50' in result['formatted_balance']


class TestTransactionHistoryBusinessRules:
    """
    Pruebas para las reglas de negocio del historial de transacciones
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "test_user_123"
    
    @patch('funds.models.Transaction.get_user_transactions')
    @patch('funds.models.Fund.get')
    def test_get_transaction_history_with_fund_names(self, mock_fund, mock_transactions):
        """
        Prueba: El historial incluye nombres de fondos y formateo correcto
        
        Regla de negocio: Las transacciones deben incluir información enriquecida del fondo
        """
        # Arrange
        mock_transaction = Mock()
        mock_transaction.fund_id = "fund_123"
        mock_transaction.amount = 125000
        mock_transaction.transaction_type = 'SUBSCRIPTION'
        mock_transaction.to_dict.return_value = {
            'id': 'txn_123',
            'fund_id': 'fund_123',
            'amount': 125000,
            'transaction_type': 'SUBSCRIPTION'
        }
        mock_transactions.return_value = [mock_transaction]
        
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund.return_value = mock_fund_obj
        
        # Act
        result = self.fund_service.get_user_transaction_history(self.test_user_id, limit=10)
        
        # Assert
        assert len(result) == 1
        assert result[0]['fund_name'] == "Fondo FPV Conservador"
        assert result[0]['formatted_amount'] == "COP $125,000.00"
        assert result[0]['transaction_type_display'] == 'Suscripción'
    
    @patch('funds.models.Transaction.get_user_transactions')
    @patch('funds.models.Fund.get')
    def test_transaction_history_handles_missing_fund(self, mock_fund, mock_transactions):
        """
        Prueba: El historial maneja fondos eliminados correctamente
        
        Regla de negocio: Si un fondo ya no existe, mostrar mensaje descriptivo
        """
        # Arrange
        mock_transaction = Mock()
        mock_transaction.fund_id = "fund_deleted"
        mock_transaction.amount = 125000
        mock_transaction.transaction_type = 'SUBSCRIPTION'
        mock_transaction.to_dict.return_value = {
            'id': 'txn_123',
            'fund_id': 'fund_deleted',
            'amount': 125000,
            'transaction_type': 'SUBSCRIPTION'
        }
        mock_transactions.return_value = [mock_transaction]
        
        mock_fund.side_effect = Fund.DoesNotExist()
        
        # Act
        result = self.fund_service.get_user_transaction_history(self.test_user_id, limit=10)
        
        # Assert
        assert len(result) == 1
        assert result[0]['fund_name'] == "Fondo no encontrado"


@pytest.mark.integration
class TestFundServiceIntegration:
    """
    Pruebas de integración completas que verifican flujos completos
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "integration_user_123"
        self.test_fund_id = "integration_fund_456"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    @patch('funds.models.Transaction.get_user_transactions')
    def test_complete_subscription_and_cancellation_flow(self, mock_user_transactions, mock_transaction, mock_balance, mock_fund):
        """
        Prueba: Flujo completo de suscripción seguido de cancelación
        
        Regla de negocio: Un usuario puede suscribirse y luego cancelar, recuperando su dinero
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo FPV Conservador"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 500000
        mock_balance_obj.update_balance.return_value = True
        mock_balance.return_value = mock_balance_obj
        
        # Mock para suscripción
        mock_subscription_txn = Mock()
        mock_subscription_txn.to_dict.return_value = {
            'id': 'txn_sub_123',
            'transaction_type': 'SUBSCRIPTION',
            'status': 'COMPLETED'
        }
        mock_subscription_txn.save = Mock()
        mock_subscription_txn.update_status = Mock()
        
        # Mock para cancelación
        mock_cancellation_txn = Mock()
        mock_cancellation_txn.to_dict.return_value = {
            'id': 'txn_cancel_123',
            'transaction_type': 'CANCELLATION',
            'status': 'COMPLETED'
        }
        mock_cancellation_txn.save = Mock()
        mock_cancellation_txn.update_status = Mock()
        
        mock_transaction.side_effect = [mock_subscription_txn, mock_cancellation_txn]
        
        # Para la cancelación - simular transacción de suscripción existente
        mock_existing_subscription = Mock()
        mock_existing_subscription.fund_id = self.test_fund_id
        mock_existing_subscription.transaction_type = 'SUBSCRIPTION'
        mock_existing_subscription.status = 'COMPLETED'
        mock_existing_subscription.amount = 125000
        mock_existing_subscription.created_at = datetime(2023, 1, 1)
        mock_user_transactions.return_value = [mock_existing_subscription]
        
        # Act & Assert - Suscripción
        success_sub, message_sub, data_sub = self.fund_service.subscribe_to_fund(
            self.test_user_id, self.test_fund_id
        )
        assert success_sub is True
        assert "Suscripción exitosa" in message_sub
        
        # Act & Assert - Cancelación
        success_cancel, message_cancel, data_cancel = self.fund_service.cancel_fund_subscription(
            self.test_user_id, self.test_fund_id
        )
        assert success_cancel is True
        assert "Cancelación exitosa" in message_cancel
        
        # Verificar llamadas a actualización de saldo
        assert mock_balance_obj.update_balance.call_count == 2
        # Primera llamada: 500k - 125k = 375k (suscripción)
        # Segunda llamada: saldo actual + 125k (cancelación)
