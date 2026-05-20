"""
AI Engine URLs — SakinaFinance
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_dashboard, name='ai_engine_dashboard'),
    path('api/forecast/', views.ai_forecast_api, name='ai_forecast_api'),
    path('api/chat/sessions/', views.api_chat_sessions, name='api_chat_sessions'),
    path('api/chat/sessions/<uuid:session_id>/', views.api_chat_session_detail, name='api_chat_session_detail'),
    path('api/chat/', views.api_ai_chat, name='api_ai_chat'),
    path('api/knowledge/upload/', views.api_upload_knowledge, name='api_upload_knowledge'),
    path('api/ocr/documents/', views.api_ocr_documents, name='api_ocr_documents'),
    path('api/ocr/documents/<uuid:document_id>/', views.api_ocr_document_detail, name='api_ocr_document_detail'),
    path('api/ocr/documents/<uuid:document_id>/validate/', views.api_ocr_validate_document, name='api_ocr_validate_document'),
    path('api/rag-test/', views.api_test_rag_service, name='api_test_rag_service'),
]
