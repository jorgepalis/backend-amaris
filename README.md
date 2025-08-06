# 🏦 Sistema de Gestión de Fondos - Prueba Técnica

Sistema backend completo para gestión de fondos de inversión desarrollado con Django, Django REST Framework y DynamoDB. Implementa una arquitectura robusta con validaciones basadas en serializers y separación clara de responsabilidades.

## 🚀 Características Principales

### 📊 **Gestión de Fondos**
- ✅ Listado de 5 fondos predefinidos (FPV/FIC)
- ✅ Suscripción con validación automática de saldo y duplicados
- ✅ Cancelación con reembolso automático del monto invertido
- ✅ Validación de montos mínimos por fondo
- ✅ Tracking preciso de inversiones con campo `invested_amount`

### 👤 **Gestión de Usuario**
- ✅ Usuario único del sistema ($500.000 saldo inicial)
- ✅ Consulta de saldo disponible en tiempo real
- ✅ Historial completo de transacciones enriquecido
- ✅ Fondos activos del usuario con detalles completos
- ✅ Información personal completa del usuario

### 🔔 **Sistema de Notificaciones**
- ✅ Preferencias personalizables (Email/SMS)
- ✅ Notificaciones automáticas en todas las transacciones
- ✅ Persistencia de preferencias por usuario
- ✅ API REST para gestión de preferencias

### 🏗️ **Arquitectura Avanzada**
- ✅ **Serializers con validaciones de negocio** - Toda la lógica de validación centralizada
- ✅ **DynamoDB con 6 tablas optimizadas** - Esquema NoSQL eficiente
- ✅ **PynamoDB como ORM elegante** - Código limpio y mantenible
- ✅ **Documentación Swagger/OpenAPI completa** - Con ejemplos y esquemas detallados
- ✅ **Separación de responsabilidades** - Views, Serializers, Models y Services
- ✅ **Validaciones atómicas** - Sin duplicación de código

## 🗄️ Estructura de Base de Datos

### **Tablas DynamoDB:**

1. **`users`** - Información del usuario único del sistema
   - Partition Key: `user_id`
   - Campos: name, email, phone, document_number, document_type
   
2. **`funds`** - 5 fondos predefinidos (FPV/FIC) con configuración completa
   - Partition Key: `id`
   - Campos: name, minimum_amount, category, is_active
   
3. **`user_balances`** - Saldo disponible del usuario en tiempo real
   - Partition Key: `user_id`
   - Campos: available_balance, updated_at
   
4. **`transactions`** - Historial completo de transacciones con trazabilidad
   - Partition Key: `id`
   - Campos: user_id, fund_id, transaction_type, amount, status, notification_sent
   
5. **`user_funds`** - **Tabla de suscripciones optimizada** para consultas rápidas
   - Partition Key: `user_id`, Sort Key: `fund_id`
   - Campos: active, subscription_amount, **invested_amount**, subscribed_at, cancelled_at
   
6. **`user_notifications`** - Preferencias de notificación personalizadas
   - Partition Key: `user_id`
   - Campos: notification_type, email_enabled, sms_enabled

## 🛠️ Tecnologías Utilizadas

- **Django 4.2** - Framework web principal
- **Django REST Framework 3.14.0** - APIs REST con serializers
- **PynamoDB 5.3.4** - ORM elegante para DynamoDB
- **boto3 1.26.137** - AWS SDK (versión compatible)
- **DynamoDB** - Base de datos NoSQL de AWS
- **drf-spectacular 0.27.0** - Documentación OpenAPI automática
- **django-cors-headers 4.3.1** - Soporte CORS
- **python-decouple 3.8** - Gestión de variables de entorno

## 🎯 Arquitectura de Serializers (Núcleo del Sistema)

### **Validaciones Centralizadas:**

- **`FundSubscriptionSerializer`** - Todas las validaciones de suscripción:
  - ✅ Existencia del fondo
  - ✅ Fondo activo
  - ✅ Saldo suficiente del usuario
  - ✅ No suscripción duplicada al mismo fondo
  - ✅ Validación de monto mínimo

- **`FundCancellationSerializer`** - Validaciones de cancelación:
  - ✅ Existencia del fondo
  - ✅ Suscripción activa válida
  - ✅ Cálculo automático de reembolso

- **`NotificationPreferencesSerializer`** - Validación de preferencias:
  - ✅ Tipos válidos (email/sms)
  - ✅ Formato de datos correcto

## 📡 Endpoints API

### **🏦 Gestión de Fondos**
```
GET    /api/funds/                      # Listar fondos disponibles
GET    /api/funds/{fund_id}/            # Detalle de un fondo
POST   /api/funds/{fund_id}/subscribe/  # Suscribirse a un fondo
POST   /api/funds/{fund_id}/cancel/     # Cancelar suscripción
```

### **👤 Gestión de Usuario**
```
GET    /api/user/                       # Información del usuario
GET    /api/user/balance/               # Saldo del usuario
GET    /api/user/funds/                 # Fondos activos del usuario
GET    /api/user/transactions/          # Historial de transacciones
```

### **🔔 Preferencias de Notificación**
```
GET    /api/user/notifications/         # Obtener preferencias actuales
PUT    /api/user/notifications/         # Actualizar preferencias (email/sms)
```

### **📊 Documentación API**
```
GET    /api/docs/                       # Swagger UI interactiva
GET    /api/redoc/                      # Documentación ReDoc
GET    /api/schema/                     # Schema OpenAPI JSON
```

## 📋 Reglas de Negocio Implementadas

### **Validaciones de Suscripción (FundSubscriptionSerializer):**
- ✅ **Fondo debe existir y estar activo**
- ✅ **Usuario no puede estar suscrito al mismo fondo** (prevención de duplicados)
- ✅ **Saldo suficiente** para cubrir el monto mínimo
- ✅ **Validación de monto mínimo** específico por fondo
- ✅ **Descuento automático** del saldo disponible
- ✅ **Creación de transacción** con ID único y estado
- ✅ **Notificación automática** según preferencias del usuario
- ✅ **Tracking de monto invertido** en campo dedicated

### **Validaciones de Cancelación (FundCancellationSerializer):**
- ✅ **Fondo debe existir**
- ✅ **Usuario debe tener suscripción activa** al fondo
- ✅ **Reembolso del monto exacto invertido** (invested_amount)
- ✅ **Actualización de estado** en tabla UserFund
- ✅ **Transacción de cancelación** con trazabilidad completa
- ✅ **Notificación de cancelación** exitosa

### **Gestión de Notificaciones:**
- ✅ **Preferencias por defecto: Email**
- ✅ **Cambio dinámico** entre Email/SMS via API
- ✅ **Uso automático** de preferencias en todas las transacciones
- ✅ **Validación de tipos** permitidos (email/sms únicamente)

## 🔧 Configuración e Instalación

### **1. Clonar el Proyecto**
```bash
git clone <repository-url>
cd prueba-tecnica-amaris
```

### **2. Instalar Dependencias**
```bash
# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias desde requirements.txt
pip install -r backend/requirements.txt
```

### **3. Configurar Variables de Entorno**
Crear archivo `.env` en la raíz del proyecto:
```env
# AWS Credentials (requerido)
AWS_ACCESS_KEY_ID=tu_access_key_aquí
AWS_SECRET_ACCESS_KEY=tu_secret_key_aquí
AWS_DEFAULT_REGION=us-east-1

# DynamoDB Configuration
DYNAMODB_TABLE_PREFIX=funds_

# Django Configuration (opcional)
DEBUG=True
SECRET_KEY=tu_secret_key_django
```

### **4. Configurar Base de Datos DynamoDB**
```bash
# Navegar al directorio de la aplicación
cd backend/funds

# Ejecutar script de configuración inicial
# Esto creará las 6 tablas y poblará con datos de prueba
python setup_simple.py
```

### **5. Ejecutar Servidor de Desarrollo**
```bash
# Desde el directorio backend
cd backend
python manage.py runserver

# El servidor estará disponible en: http://127.0.0.1:8000
```

### **6. Verificar Instalación**
- **API Docs:** http://127.0.0.1:8000/api/docs/
- **Health Check:** http://127.0.0.1:8000/api/funds/
- **Usuario Info:** http://127.0.0.1:8000/api/user/

## 📚 Documentación API

- **Swagger UI:** `http://127.0.0.1:8000/api/docs/`
- **ReDoc:** `http://127.0.0.1:8000/api/redoc/`
- **Schema JSON:** `http://127.0.0.1:8000/api/schema/`

## 📊 Fondos Predefinidos

| Nombre | Categoría | Monto Mínimo |
|--------|-----------|--------------|
| FPV_EL CLIENTE_RECAUDADORA | FPV | $75.000 |
| FPV_EL CLIENTE_ECOPETROL | FPV | $125.000 |
| DEUDAPRIVADA | FIC | $50.000 |
| FDO-ACCIONES | FIC | $250.000 |
| FPV_EL CLIENTE_DINAMICA | FPV | $100.000 |

## 🧪 Ejemplos de Uso

### **Listar Fondos Disponibles**
```bash
GET http://127.0.0.1:8000/api/funds/

# Respuesta:
{
  "success": true,
  "data": [
    {
      "id": "FPV_BTG_RECAUDADORA",
      "name": "FPV_EL CLIENTE_RECAUDADORA",
      "minimum_amount": "75000.00",
      "category": "FPV",
      "is_active": true
    }
  ],
  "message": "Se encontraron 5 fondos disponibles"
}
```

### **Suscribirse a un Fondo**
```bash
POST http://127.0.0.1:8000/api/funds/FPV_BTG_RECAUDADORA/subscribe/
Content-Type: application/json

# Sin body - usa validaciones automáticas del serializer

# Respuesta exitosa:
{
  "success": true,
  "message": "Suscripción exitosa al fondo FPV_EL CLIENTE_RECAUDADORA",
  "data": {
    "transaction_id": "trans_abc123",
    "user_name": "Usuario Prueba",
    "fund_name": "FPV_EL CLIENTE_RECAUDADORA",
    "amount": "75000.00",
    "new_balance": "425000.00",
    "notification_sent": true,
    "notification_type": "email"
  }
}
```

### **Cancelar Suscripción**
```bash
POST http://127.0.0.1:8000/api/funds/FPV_BTG_RECAUDADORA/cancel/
Content-Type: application/json

# Sin body - usa validaciones del FundCancellationSerializer

# Respuesta:
{
  "success": true,
  "message": "Cancelación exitosa del fondo FPV_EL CLIENTE_RECAUDADORA",
  "data": {
    "transaction_id": "trans_def456",
    "fund_name": "FPV_EL CLIENTE_RECAUDADORA",
    "refund_amount": "75000.00",
    "new_balance": "500000.00",
    "notification_sent": true
  }
}
```

### **Actualizar Preferencias de Notificación**
```bash
PUT http://127.0.0.1:8000/api/user/notifications/
Content-Type: application/json

{
  "notification_type": "sms"
}

# Respuesta:
{
  "success": true,
  "data": {
    "user_id": "user_default",
    "notification_type": "sms",
    "email_enabled": false,
    "sms_enabled": true,
    "updated_at": "2025-08-04T10:30:00Z"
  },
  "message": "Preferencias actualizadas a: sms"
}
```

### **Consultar Saldo del Usuario**
```bash
GET http://127.0.0.1:8000/api/user/balance/

# Respuesta:
{
  "success": true,
  "data": {
    "user_id": "user_default",
    "available_balance": "500000.00",
    "formatted_balance": "COP $500,000.00",
    "updated_at": "2025-08-04T10:30:00Z"
  },
  "message": "Saldo obtenido exitosamente"
}
```

### **Ver Fondos Activos del Usuario**
```bash
GET http://127.0.0.1:8000/api/user/funds/

# Respuesta:
{
  "success": true,
  "data": [
    {
      "subscription": {
        "user_id": "user_default",
        "fund_id": "FPV_BTG_RECAUDADORA",
        "active": true,
        "subscription_amount": "75000.00",
        "invested_amount": "75000.00",
        "subscribed_at": "2025-08-04T10:30:00Z"
      },
      "fund": {
        "id": "FPV_BTG_RECAUDADORA",
        "name": "FPV_EL CLIENTE_RECAUDADORA",
        "minimum_amount": "75000.00",
        "category": "FPV"
      }
    }
  ],
  "message": "Se encontraron 1 fondos activos"
}
```

## 🔍 Validaciones Implementadas

### **A Nivel de Serializer (Arquitectura Centralizada):**

- ✅ **Validación de existencia de fondos** - FundSubscriptionSerializer y FundCancellationSerializer
- ✅ **Validación de fondos activos** - Solo fondos con `is_active=True`
- ✅ **Saldo suficiente** - Verificación antes de cada suscripción
- ✅ **Prevención de duplicados** - No permitir suscripción al mismo fondo activo
- ✅ **Suscripción activa** - Verificación antes de cancelar
- ✅ **Tipos de notificación válidos** - Solo "email" o "sms"
- ✅ **Montos mínimos por fondo** - Validación específica por tipo de fondo
- ✅ **Integridad de datos** - Validación de tipos y formatos

### **Validaciones de Negocio en FundSubscriptionSerializer:**
```python
def validate(self, attrs):
    # 1. Verificar que el fondo existe y está activo
    # 2. Obtener saldo del usuario
    # 3. Verificar que no esté suscrito al mismo fondo
    # 4. Verificar saldo suficiente para monto mínimo
    # 5. Retornar datos validados para la vista
```

### **Validaciones de Negocio en FundCancellationSerializer:**
```python
def validate(self, attrs):
    # 1. Verificar que el fondo existe
    # 2. Verificar que tiene suscripción activa
    # 3. Calcular monto de reembolso (invested_amount)
    # 4. Retornar datos para procesamiento
```

## 💡 Características Avanzadas

### **🏗️ Arquitectura de Serializers:**
- **Separación de responsabilidades** - Views solo manejan HTTP, validaciones en Serializers
- **Validaciones centralizadas** - Toda la lógica de negocio en un lugar
- **Reutilización de código** - Eliminación de duplicación
- **Fácil testing** - Validaciones aisladas y testeable
- **Mantenimiento simplificado** - Cambios en un solo lugar

### **🔄 Tabla UserFund Optimizada:**
- **Composite Key** (user_id + fund_id) para consultas eficientes
- **Campo invested_amount** para tracking preciso de inversiones
- **Estados de suscripción** (active/inactive) con timestamps
- **Reactivación inteligente** de suscripciones canceladas
- **Consultas rápidas** para fondos activos por usuario

### **📊 Sistema de Transacciones Robusto:**
- **IDs únicos** generados automáticamente
- **Estados de transacción** (PENDING → COMPLETED/FAILED)
- **Rollback automático** en caso de errores
- **Trazabilidad completa** de todas las operaciones
- **Notificaciones integradas** con flag de envío

### **🔔 Notificaciones Personalizadas:**
- **Preferencias por usuario** almacenadas en DynamoDB
- **Integración automática** en todas las transacciones
- **Fallback inteligente** a email por defecto
- **API dedicada** para gestión de preferencias
- **Extensible** para nuevos tipos de notificación

### **📚 Documentación Automática:**
- **Swagger UI interactiva** con ejemplos reales
- **Schemas detallados** para cada endpoint
- **Validaciones documentadas** automáticamente
- **Ejemplos de request/response** para cada caso de uso

## 🧪 Testing y Verificación

### **Casos de Prueba Implementados:**

1. **Suscripción Exitosa:**
   - Usuario con saldo suficiente
   - Fondo activo y existente
   - Sin suscripción previa al mismo fondo

2. **Validación de Saldo Insuficiente:**
   - Intentar suscribirse con saldo menor al mínimo
   - Verificar mensaje de error apropiado

3. **Prevención de Duplicados:**
   - Intentar suscribirse al mismo fondo activo dos veces
   - Verificar rechazo de la segunda suscripción

4. **Cancelación Exitosa:**
   - Usuario con suscripción activa
   - Reembolso del monto exacto invertido

5. **Preferencias de Notificación:**
   - Cambio entre email y SMS
   - Validación de tipos inválidos

### **Comandos de Testing:**
```bash
# Probar configuración inicial
python backend/funds/setup_simple.py

# Verificar endpoints básicos
curl http://127.0.0.1:8000/api/funds/
curl http://127.0.0.1:8000/api/user/balance/

# Probar suscripción
curl -X POST http://127.0.0.1:8000/api/funds/FPV_BTG_RECAUDADORA/subscribe/

# Verificar fondos activos
curl http://127.0.0.1:8000/api/user/funds/
```

## 🔧 Estructura del Proyecto

```
prueba-tecnica-amaris/
├── README.md                    # Documentación completa
├── prueba-tecnica-generica.pdf  # Especificaciones originales
└── backend/                     # Aplicación Django
    ├── core/                    # Configuración del proyecto
    │   ├── settings.py         # Configuración con DRF y DynamoDB
    │   ├── urls.py             # URLs principales
    │   └── wsgi.py
    ├── funds/                   # Aplicación principal
    │   ├── models.py           # Modelos PynamoDB (6 tablas)
    │   ├── serializers.py      # Validaciones centralizadas ⭐
    │   ├── views.py            # Views con serializers ⭐
    │   ├── services.py         # Lógica de notificaciones
    │   ├── urls.py             # Rutas de la API
    │   └── setup_simple.py     # Script de configuración inicial
    ├── requirements.txt         # Dependencias del proyecto
    └── manage.py               # Comando de Django
```

## ⚡ Rendimiento y Escalabilidad

### **Optimizaciones Implementadas:**
- **Consultas eficientes** con Partition Key + Sort Key en DynamoDB
- **Índices optimizados** para consultas frecuentes
- **Serializers cacheable** para validaciones repetitivas
- **Respuestas ligeras** con datos esenciales
- **Logging estructurado** para debugging

### **Preparado para Escalar:**
- **DynamoDB serverless** - escalado automático
- **Arquitectura stateless** - múltiples instancias
- **APIs RESTful** - integración sencilla
- **Validaciones desacopladas** - fácil mantenimiento

---

## 🚀 Próximos Pasos Sugeridos

1. **Testing Automatizado** - Implementar test suite completo
2. **Cache Redis** - Para consultas frecuentes de fondos
3. **Logging Avanzado** - CloudWatch integration
4. **Monitoreo** - Health checks y métricas
5. **CI/CD Pipeline** - Deployment automatizado
6. **Autenticación** - JWT para múltiples usuarios
7. **WebSockets** - Notificaciones en tiempo real

---

**✨ Desarrollado paso a paso siguiendo las especificaciones de la prueba técnica con arquitectura robusta y escalable** 🏗️
