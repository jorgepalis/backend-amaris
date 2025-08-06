"""
URLs para la app de fondos
"""

from django.urls import path
from .views import (
    FundListView,
    FundDetailView,
    FundSubscribeView,
    FundCancellationView,
    UserBalanceView,
    TransactionHistoryView,
    UserDetailView,
    UserActiveFundsView,
    UserNotificationPreferencesView,
    UpdateNotificationPreferencesView
)

app_name = 'funds'

urlpatterns = [
    # Gestión de fondos
    path('funds/', FundListView.as_view(), name='fund-list'),
    path('funds/<str:fund_id>/', FundDetailView.as_view(), name='fund-detail'),
    path('funds/<str:fund_id>/subscribe/', FundSubscribeView.as_view(), name='fund-subscribe'),
    path('funds/<str:fund_id>/cancel/', FundCancellationView.as_view(), name='fund-cancel'),
    
    # Gestión de usuario
    path('user/', UserDetailView.as_view(), name='user-detail'),
    path('user/balance/', UserBalanceView.as_view(), name='user-balance'),
    path('user/funds/', UserActiveFundsView.as_view(), name='user-active-funds'),
    path('user/transactions/', TransactionHistoryView.as_view(), name='user-transactions'),
    
    # Preferencias de notificación
    path('user/notifications/', UserNotificationPreferencesView.as_view(), name='user-notification-preferences'),
    path('user/notifications/update/', UpdateNotificationPreferencesView.as_view(), name='update-notification-preferences'),
]
