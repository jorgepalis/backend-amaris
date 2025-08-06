"""
Pruebas para validar casos edge y reglas de negocio específicas
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from funds.services import FundService


class TestEdgeCasesAndBusinessRules:
    """
    Pruebas para casos edge y reglas de negocio específicas
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "edge_case_user"
        self.test_fund_id = "edge_case_fund"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    def test_subscription_exact_minimum_amount(self, mock_balance, mock_fund):
        """
        Prueba: Suscripción cuando el usuario tiene exactamente el monto mínimo
        
        Regla de negocio: Se debe permitir la suscripción cuando el saldo = monto mínimo
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo Exacto"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 125000  # Exactamente el mínimo
        mock_balance.return_value = mock_balance_obj
        
        with patch('funds.models.Transaction.create_transaction') as mock_transaction:
            mock_transaction_obj = Mock()
            mock_transaction_obj.save = Mock()
            mock_transaction_obj.update_status = Mock()
            mock_transaction_obj.to_dict.return_value = {'status': 'COMPLETED'}
            mock_transaction.return_value = mock_transaction_obj
            mock_balance_obj.update_balance.return_value = True
            
            # Act
            success, message, transaction_data = self.fund_service.subscribe_to_fund(
                self.test_user_id, self.test_fund_id
            )
            
            # Assert
            assert success is True
            assert "Suscripción exitosa" in message
            mock_balance_obj.update_balance.assert_called_once_with(Decimal('0'))  # Queda en 0
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    def test_subscription_one_peso_short(self, mock_balance, mock_fund):
        """
        Prueba: Suscripción falla cuando falta 1 peso
        
        Regla de negocio: No se permite suscripción si falta aunque sea 1 peso
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo Casi"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 124999  # Le falta 1 peso
        mock_balance.return_value = mock_balance_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "No tiene saldo disponible" in message
        assert transaction_data is None
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.Transaction.get_user_transactions')
    def test_multiple_subscriptions_to_same_fund(self, mock_user_transactions, mock_fund):
        """
        Prueba: Múltiples suscripciones al mismo fondo - solo se puede cancelar la más reciente activa
        
        Regla de negocio: Si hay múltiples suscripciones, cancelar la más reciente no cancelada
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo Multiple"
        mock_fund.return_value = mock_fund_obj
        
        # Simular múltiples suscripciones
        old_subscription = Mock()
        old_subscription.fund_id = self.test_fund_id
        old_subscription.transaction_type = 'SUBSCRIPTION'
        old_subscription.status = 'COMPLETED'
        old_subscription.amount = 125000
        old_subscription.created_at = datetime(2023, 1, 1)
        
        old_cancellation = Mock()
        old_cancellation.fund_id = self.test_fund_id
        old_cancellation.transaction_type = 'CANCELLATION'
        old_cancellation.status = 'COMPLETED'
        old_cancellation.created_at = datetime(2023, 1, 5)  # Cancela la primera
        
        recent_subscription = Mock()
        recent_subscription.fund_id = self.test_fund_id
        recent_subscription.transaction_type = 'SUBSCRIPTION'
        recent_subscription.status = 'COMPLETED'
        recent_subscription.amount = 150000
        recent_subscription.created_at = datetime(2023, 2, 1)  # Más reciente
        
        # Orden: más reciente primero (como viene de la query)
        mock_user_transactions.return_value = [recent_subscription, old_cancellation, old_subscription]
        
        with patch('funds.models.UserBalance.get_or_create_balance') as mock_balance:
            with patch('funds.models.Transaction.create_transaction') as mock_transaction:
                mock_balance_obj = Mock()
                mock_balance_obj.available_balance = 200000
                mock_balance_obj.update_balance.return_value = True
                mock_balance.return_value = mock_balance_obj
                
                mock_transaction_obj = Mock()
                mock_transaction_obj.save = Mock()
                mock_transaction_obj.update_status = Mock()
                mock_transaction_obj.to_dict.return_value = {
                    'amount': 150000,  # Debe devolver el monto de la suscripción más reciente
                    'transaction_type': 'CANCELLATION'
                }
                mock_transaction.return_value = mock_transaction_obj
                
                # Act
                success, message, transaction_data = self.fund_service.cancel_fund_subscription(
                    self.test_user_id, self.test_fund_id
                )
                
                # Assert
                assert success is True
                assert "Cancelación exitosa" in message
                # Debe devolver 150k (de la suscripción más reciente) + 200k = 350k
                mock_balance_obj.update_balance.assert_called_once_with(Decimal('350000'))
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.Transaction.get_user_transactions')
    def test_cancellation_of_subscription_different_fund(self, mock_user_transactions, mock_fund):
        """
        Prueba: No se puede cancelar suscripción de un fondo cuando la activa es de otro fondo
        
        Regla de negocio: Las cancelaciones son específicas por fondo
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo A"
        mock_fund.return_value = mock_fund_obj
        
        # Suscripción activa pero a un fondo diferente
        subscription_other_fund = Mock()
        subscription_other_fund.fund_id = "otro_fondo_id"  # Diferente al que queremos cancelar
        subscription_other_fund.transaction_type = 'SUBSCRIPTION'
        subscription_other_fund.status = 'COMPLETED'
        subscription_other_fund.amount = 125000
        subscription_other_fund.created_at = datetime(2023, 1, 1)
        
        mock_user_transactions.return_value = [subscription_other_fund]
        
        # Act
        success, message, transaction_data = self.fund_service.cancel_fund_subscription(
            self.test_user_id, self.test_fund_id  # Intentamos cancelar fondo diferente
        )
        
        # Assert
        assert success is False
        assert "No tiene una suscripción activa" in message
        assert transaction_data is None


class TestDecimalPrecisionAndMoneyHandling:
    """
    Pruebas para verificar el manejo correcto de precisión decimal y dinero
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "decimal_user"
        self.test_fund_id = "decimal_fund"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    def test_decimal_precision_in_calculations(self, mock_transaction, mock_balance, mock_fund):
        """
        Prueba: Las operaciones monetarias mantienen precisión decimal correcta
        
        Regla de negocio: Los cálculos de dinero deben ser exactos, sin errores de punto flotante
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo Decimal"
        mock_fund_obj.minimum_amount = 125000.50  # Con decimales
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 500000.75  # Con decimales
        mock_balance_obj.update_balance.return_value = True
        mock_balance.return_value = mock_balance_obj
        
        mock_transaction_obj = Mock()
        mock_transaction_obj.save = Mock()
        mock_transaction_obj.update_status = Mock()
        mock_transaction_obj.to_dict.return_value = {'status': 'COMPLETED'}
        mock_transaction.return_value = mock_transaction_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, self.test_fund_id
        )
        
        # Assert
        assert success is True
        # Verificar que el cálculo decimal es exacto: 500000.75 - 125000.50 = 375000.25
        expected_balance = Decimal('375000.25')
        mock_balance_obj.update_balance.assert_called_once_with(expected_balance)
    
    @patch('funds.models.UserBalance.get_or_create_balance')
    def test_balance_formatting_with_large_numbers(self, mock_balance):
        """
        Prueba: El formateo de saldos grandes funciona correctamente
        
        Regla de negocio: Los saldos deben formatearse con separadores de miles
        """
        # Arrange
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 1234567.89  # Número grande con decimales
        mock_balance.return_value = mock_balance_obj
        
        # Act
        result = self.fund_service.get_user_balance(self.test_user_id)
        
        # Assert
        assert result['available_balance'] == Decimal('1234567.89')
        formatted = result['formatted_balance']
        assert 'COP $' in formatted
        assert '1,234,567.89' in formatted
    
    def test_zero_balance_handling(self):
        """
        Prueba: El manejo de saldo cero es correcto
        
        Regla de negocio: Un saldo de 0 debe mostrarse como "COP $0.00"
        """
        with patch('funds.models.UserBalance.get_or_create_balance') as mock_balance:
            mock_balance_obj = Mock()
            mock_balance_obj.available_balance = 0
            mock_balance.return_value = mock_balance_obj
            
            # Act
            result = self.fund_service.get_user_balance(self.test_user_id)
            
            # Assert
            assert result['available_balance'] == Decimal('0')
            assert 'COP $0.00' in result['formatted_balance']


class TestConcurrencyAndRaceConditions:
    """
    Pruebas para verificar el manejo de condiciones de carrera y concurrencia
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "concurrent_user"
        self.test_fund_id = "concurrent_fund"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    def test_transaction_rollback_on_balance_update_failure(self, mock_transaction, mock_balance, mock_fund):
        """
        Prueba: Si falla la actualización de saldo, la transacción se marca como fallida
        
        Regla de negocio: Garantizar consistencia - si algo falla, marcar transacción como FAILED
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo Rollback"
        mock_fund_obj.minimum_amount = 125000
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 500000
        mock_balance_obj.update_balance.return_value = False  # Simular fallo
        mock_balance.return_value = mock_balance_obj
        
        mock_transaction_obj = Mock()
        mock_transaction_obj.save = Mock()
        mock_transaction_obj.update_status = Mock()
        mock_transaction.return_value = mock_transaction_obj
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "Error procesando la transacción" in message
        assert transaction_data is None
        # Verificar que se marcó como fallida
        mock_transaction_obj.update_status.assert_called_once_with('FAILED')
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.Transaction.get_user_transactions')
    @patch('funds.models.UserBalance.get_or_create_balance')
    @patch('funds.models.Transaction.create_transaction')
    def test_cancellation_rollback_on_balance_update_failure(self, mock_transaction, mock_balance, mock_user_transactions, mock_fund):
        """
        Prueba: Si falla la devolución de dinero en cancelación, marcar transacción como fallida
        
        Regla de negocio: La cancelación debe ser atómica - o se completa todo o nada
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = "Fondo Rollback Cancel"
        mock_fund.return_value = mock_fund_obj
        
        # Simular suscripción activa
        mock_subscription = Mock()
        mock_subscription.fund_id = self.test_fund_id
        mock_subscription.transaction_type = 'SUBSCRIPTION'
        mock_subscription.status = 'COMPLETED'
        mock_subscription.amount = 125000
        mock_subscription.created_at = datetime(2023, 1, 1)
        mock_user_transactions.return_value = [mock_subscription]
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = 100000
        mock_balance_obj.update_balance.return_value = False  # Simular fallo en devolución
        mock_balance.return_value = mock_balance_obj
        
        mock_transaction_obj = Mock()
        mock_transaction_obj.save = Mock()
        mock_transaction_obj.update_status = Mock()
        mock_transaction.return_value = mock_transaction_obj
        
        # Act
        success, message, transaction_data = self.fund_service.cancel_fund_subscription(
            self.test_user_id, self.test_fund_id
        )
        
        # Assert
        assert success is False
        assert "Error procesando la cancelación" in message
        assert transaction_data is None
        # Verificar que se marcó como fallida
        mock_transaction_obj.update_status.assert_called_once_with('FAILED')


@pytest.mark.parametrize("minimum_amount,user_balance,should_succeed", [
    (125000, 125000, True),    # Exactamente el mínimo
    (125000, 125001, True),    # Un peso más del mínimo
    (125000, 124999, False),   # Un peso menos del mínimo
    (500000, 1000000, True),   # Saldo abundante
    (1000000, 999999, False),  # Casi el mínimo pero no alcanza
    (0, 0, True),              # Caso edge: fondo gratuito
    (100, 99.99, False),       # Diferencia por centavos
])
class TestParametrizedBusinessRules:
    """
    Pruebas parametrizadas para verificar reglas de negocio con diferentes combinaciones
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba"""
        self.fund_service = FundService()
        self.test_user_id = "param_user"
        self.test_fund_id = "param_fund"
    
    @patch('funds.models.Fund.get')
    @patch('funds.models.UserBalance.get_or_create_balance')
    def test_subscription_balance_validation(self, mock_balance, mock_fund, minimum_amount, user_balance, should_succeed):
        """
        Prueba parametrizada: Validación de saldo para suscripción con diferentes valores
        
        Regla de negocio: Suscripción exitosa solo si saldo >= monto mínimo
        """
        # Arrange
        mock_fund_obj = Mock()
        mock_fund_obj.name = f"Fondo {minimum_amount}"
        mock_fund_obj.minimum_amount = minimum_amount
        mock_fund_obj.is_active = True
        mock_fund.return_value = mock_fund_obj
        
        mock_balance_obj = Mock()
        mock_balance_obj.available_balance = user_balance
        mock_balance.return_value = mock_balance_obj
        
        if should_succeed:
            with patch('funds.models.Transaction.create_transaction') as mock_transaction:
                mock_transaction_obj = Mock()
                mock_transaction_obj.save = Mock()
                mock_transaction_obj.update_status = Mock()
                mock_transaction_obj.to_dict.return_value = {'status': 'COMPLETED'}
                mock_transaction.return_value = mock_transaction_obj
                mock_balance_obj.update_balance.return_value = True
        
        # Act
        success, message, transaction_data = self.fund_service.subscribe_to_fund(
            self.test_user_id, self.test_fund_id
        )
        
        # Assert
        assert success == should_succeed
        if should_succeed:
            assert "Suscripción exitosa" in message
            assert transaction_data is not None
        else:
            assert "No tiene saldo disponible" in message
            assert transaction_data is None
