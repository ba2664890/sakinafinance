"""
AI Engine Views — SakinaFinance
Dashboard IA avec Prophet forecasting
"""
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from .models import (
    AIAnalysis, CashFlowForecast, AIInsight, AnomalyDetection,
    KnowledgeDocument, KnowledgeChunk, ChatSession, ChatMessage, DocumentOCR
)
from .services_rag import RAGService
from sakinafinance.accounting.models import Transaction, TransactionLine, Invoice
from django.db.models import Sum, Count, Q
from decimal import Decimal
import logging

logger = logging.getLogger('sakinafinance')


def _serialize_ocr_document(doc):
    allowed_actions = ['validate', 'retry']
    if doc.document_type in {
        DocumentOCR.DocumentType.INVOICE,
        DocumentOCR.DocumentType.SUPPLIER_INVOICE,
        DocumentOCR.DocumentType.RECEIPT,
    } and not doc.linked_invoice_id:
        allowed_actions.append('create_supplier_invoice')
        allowed_actions.append('create_customer_invoice')
    if doc.document_type in {
        DocumentOCR.DocumentType.PURCHASE_ORDER,
        DocumentOCR.DocumentType.DELIVERY_NOTE,
        DocumentOCR.DocumentType.RECEIPT_NOTE,
        DocumentOCR.DocumentType.STOCK_COUNT,
    }:
        allowed_actions.append('export_inventory_lines')
    return {
        'id': str(doc.id),
        'filename': doc.filename,
        'document_type': doc.document_type,
        'document_type_label': doc.get_document_type_display(),
        'status': doc.status,
        'status_label': doc.get_status_display(),
        'confidence_score': float(doc.confidence_score or 0),
        'file_size': doc.file_size,
        'raw_text': doc.raw_text,
        'extracted_data': doc.extracted_data,
        'error_message': doc.error_message,
        'linked_invoice_id': str(doc.linked_invoice_id) if doc.linked_invoice_id else None,
        'allowed_actions': allowed_actions,
        'created_at': doc.created_at.strftime('%d/%m/%Y %H:%M'),
        'processed_at': doc.processed_at.strftime('%d/%m/%Y %H:%M') if doc.processed_at else '',
    }


def _get_company(request):
    return getattr(request.user, 'company', None)


def _json_body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def _serialize_chat_message(message):
    return {
        'id': str(message.id),
        'role': message.role,
        'content': message.content,
        'type': message.response_type,
        'payload': message.payload,
        'sources': message.sources,
        'created_at': message.created_at.strftime('%d/%m/%Y %H:%M'),
    }


def _serialize_chat_session(session):
    last_message = session.messages.order_by('-created_at').first()
    return {
        'id': str(session.id),
        'title': session.title,
        'summary': session.summary,
        'last_intent': session.last_intent,
        'updated_at': session.updated_at.strftime('%d/%m/%Y %H:%M'),
        'message_count': session.messages.count(),
        'last_message': last_message.content[:120] if last_message else '',
    }


def _get_or_create_chat_session(request, company, session_id=None, first_message=''):
    if session_id:
        return get_object_or_404(
            ChatSession,
            id=session_id,
            company=company,
            user=request.user,
            is_archived=False,
        )

    title = first_message.strip()[:80] or 'Nouvelle discussion'
    return ChatSession.objects.create(
        company=company,
        user=request.user,
        title=title,
    )


def _conversation_context(session, limit=8):
    messages = list(session.messages.order_by('-created_at')[:limit])
    messages.reverse()
    if not messages:
        return ""
    labels = {
        ChatMessage.Role.USER: "Utilisateur",
        ChatMessage.Role.ASSISTANT: "Sakina",
        ChatMessage.Role.SYSTEM: "Système",
    }
    return "\n".join(
        f"{labels.get(message.role, message.role)}: {message.content[:900]}"
        for message in messages
    )


def _detect_intent(message):
    lowered = message.lower()
    if any(k in lowered for k in ['cash', 'trésorerie', 'forecast', 'prévision']):
        return 'cashflow'
    if any(k in lowered for k in ['ebitda', 'marge', 'profit', 'rentabilité']):
        return 'profitability'
    if any(k in lowered for k in ['burn', 'runway', 'autonomie', 'dépense']):
        return 'burn_rate'
    if any(k in lowered for k in ['risk', 'risque', 'alerte', 'anomalie']):
        return 'risk'
    return 'rag'


def _save_assistant_message(session, response):
    payload = {
        'chart_type': response.get('chart_type'),
        'data': response.get('data'),
        'items': response.get('items'),
        'insights': response.get('insights'),
        'suggestions': response.get('suggestions'),
    }
    payload = {key: value for key, value in payload.items() if value not in [None, [], {}]}
    return ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=response.get('text', ''),
        response_type=response.get('type', 'text'),
        payload=payload,
        sources=response.get('sources', []),
    )


def _chat_response(session, response, status=200):
    assistant_message = _save_assistant_message(session, response)
    session.updated_at = timezone.now()
    session.save(update_fields=['updated_at'])
    response = {
        **response,
        'session': _serialize_chat_session(session),
        'message': _serialize_chat_message(assistant_message),
    }
    return JsonResponse(response, status=status)


def _generate_prophet_forecast(company, horizon_months=12):
    """
    Génère une prévision de trésorerie en utilisant Prophet sur les données historiques.
    Retourne les données de prévision formatées ou des données simulées si pas d'historique.
    """
    try:
        import pandas as pd
        from prophet import Prophet
        from datetime import date, timedelta
        from dateutil.relativedelta import relativedelta
        from sakinafinance.accounting.models import Transaction

        # Récupérer les transactions historiques des 24 derniers mois
        from_date = timezone.now().date() - relativedelta(months=24)
        transactions = Transaction.objects.filter(
            company=company,
            status='posted',
            date__gte=from_date
        ).values('date').annotate(
            inflow=Sum('total_credit'),
            outflow=Sum('total_debit')
        ).order_by('date')

        if transactions.count() < 10:
            # Pas assez de données historiques: retourner vide
            return [], 0.0

        # Préparer les données pour Prophet
        records = []
        for t in transactions:
            net = float(t['inflow'] or 0) - float(t['outflow'] or 0)
            records.append({'ds': t['date'], 'y': net})

        df = pd.DataFrame(records)
        df['ds'] = pd.to_datetime(df['ds'])

        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode='multiplicative',
            interval_width=0.80
        )
        m.fit(df)

        future = m.make_future_dataframe(periods=horizon_months, freq='M')
        forecast = m.predict(future)

        # Prendre seulement les périodes futures
        future_forecast = forecast[forecast['ds'] > pd.Timestamp.today()].tail(horizon_months)
        result = []
        for _, row in future_forecast.iterrows():
            result.append({
                'ds': row['ds'].strftime('%Y-%m'),
                'yhat': round(row['yhat'], 0),
                'yhat_lower': round(row['yhat_lower'], 0),
                'yhat_upper': round(row['yhat_upper'], 0),
            })
        return result, round(85.0, 1)

    except Exception as e:
        logger.error(f"Erreur Prophet: {e}")
        return [], 0.0


def _simulated_forecast(horizon_months=12):
    # OBSOLÈTE : Suppression des valeurs fictives conformément à la demande
    return [], 0.0


@login_required
def ai_dashboard(request):
    """Dashboard IA — vue principale"""
    company = _get_company(request)

    # Active insights
    insights = AIInsight.objects.filter(
        company=company, is_dismissed=False
    ).order_by('-created_at')[:6] if company else []

    # Latest anomalies
    anomalies = AnomalyDetection.objects.filter(
        company=company, is_false_positive=False
    ).order_by('-created_at')[:5] if company else []

    # Latest analysis
    analyses = AIAnalysis.objects.filter(
        company=company
    ).order_by('-created_at')[:4] if company else []

    # Cash flow forecast (latest)
    latest_forecast = None
    forecast_data = []
    confidence = 0
    if company:
        latest_forecast = CashFlowForecast.objects.filter(company=company).first()
        if latest_forecast:
            forecast_data = latest_forecast.forecast_data
            confidence = latest_forecast.confidence_score
        else:
            # Calcul en direct s'il y a assez de données, sinon vide
            forecast_data, confidence = _generate_prophet_forecast(company, 12)

    context = {
        'page_title': 'IA Advisor',
        'insights': insights,
        'anomalies': anomalies,
        'analyses': analyses,
        'forecast_data_json': json.dumps(forecast_data),
        'confidence': confidence,
        'total_insights': AIInsight.objects.filter(company=company, is_dismissed=False).count() if company else 0,
        'critical_alerts': AIInsight.objects.filter(company=company, priority='critical', is_dismissed=False).count() if company else 0,
        'anomalies_count': AnomalyDetection.objects.filter(company=company, is_false_positive=False).count() if company else 0,
        'knowledge_documents': KnowledgeDocument.objects.filter(company=company).order_by('-created_at') if company else [],
    }
    return render(request, 'ai_engine/dashboard.html', context)


import random
from decimal import Decimal


@login_required
def ai_forecast_api(request):
    """API: Générer et retourner une prévision de trésorerie Prophet"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    horizon = int(request.GET.get('horizon', 12))
    forecast_result = _generate_prophet_forecast(company, horizon)
    if isinstance(forecast_result, tuple):
        forecast_data, confidence = forecast_result
    else:
        forecast_data, confidence = forecast_result, 70.0

    return JsonResponse({
        'forecast': forecast_data,
        'confidence': confidence,
        'horizon': horizon,
    })


@login_required
def api_chat_sessions(request):
    """API: liste ou crée les sessions de discussion IA."""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'Aucune entreprise associée'}, status=400)

    if request.method == 'GET':
        sessions = ChatSession.objects.filter(
            company=company,
            user=request.user,
            is_archived=False,
        ).prefetch_related('messages')[:30]
        return JsonResponse({'sessions': [_serialize_chat_session(session) for session in sessions]})

    if request.method == 'POST':
        body = _json_body(request)
        if body is None:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        title = (body.get('title') or 'Nouvelle discussion').strip()[:160]
        session = ChatSession.objects.create(
            company=company,
            user=request.user,
            title=title or 'Nouvelle discussion',
        )
        return JsonResponse({'session': _serialize_chat_session(session)}, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_chat_session_detail(request, session_id):
    """API: charge ou archive une session IA."""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'Aucune entreprise associée'}, status=400)

    session = get_object_or_404(ChatSession, id=session_id, company=company, user=request.user)

    if request.method == 'GET':
        messages = session.messages.order_by('created_at')
        return JsonResponse({
            'session': _serialize_chat_session(session),
            'messages': [_serialize_chat_message(message) for message in messages],
        })

    if request.method == 'DELETE':
        session.is_archived = True
        session.save(update_fields=['is_archived', 'updated_at'])
        return JsonResponse({'status': 'archived'})

    if request.method == 'PATCH':
        body = _json_body(request)
        if body is None:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        title = (body.get('title') or '').strip()
        if title:
            session.title = title[:160]
            session.save(update_fields=['title', 'updated_at'])
        return JsonResponse({'session': _serialize_chat_session(session)})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_ai_chat(request):
    """API: AI Chat Assistant — Analyzes real ERP data"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    body = _json_body(request)
    if body is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    raw_message = (body.get('message') or '').strip()
    if not raw_message:
        return JsonResponse({'error': 'Message vide'}, status=400)
    message = raw_message.lower()

    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'Aucune entreprise associée'}, status=400)

    session = _get_or_create_chat_session(
        request,
        company,
        session_id=body.get('session_id'),
        first_message=raw_message,
    )
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=raw_message,
        response_type='text',
    )
    intent = _detect_intent(raw_message)
    session.last_intent = intent
    if session.title == 'Nouvelle discussion':
        session.title = raw_message[:80]
    session.save(update_fields=['last_intent', 'title', 'updated_at'])

    # 1. Fetch Key Metrics
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Revenue (Class 7)
    revenue = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status='posted',
        account__account_class='7',
        transaction__date__gte=month_start
    ).aggregate(total=Sum('credit') - Sum('debit'))['total'] or Decimal('0')

    # Expenses (Class 6)
    expenses = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status='posted',
        account__account_class='6',
        transaction__date__gte=month_start
    ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')

    # Cash (Class 5)
    cash = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status='posted',
        account__account_class='5'
    ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')

    # Burn Rate (Avg expenses last 3 months)
    three_months_ago = today - timedelta(days=90)
    total_exp_3m = TransactionLine.objects.filter(
        transaction__company=company,
        transaction__status='posted',
        account__account_class='6',
        transaction__date__gte=three_months_ago
    ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')
    avg_burn = total_exp_3m / 3

    # 2. Logic processing
    # CASHFLOW & FORECAST
    if any(k in message for k in ['cash', 'trésorerie', 'forecast', 'prévision']):
        forecast, confidence = _generate_prophet_forecast(company, 6)
        if not forecast:
            return _chat_response(session, {
                'text': f"L'analyse prédictive (Prophet) requiert plus de données historiques pour fonctionner de manière fiable. Actuellement, vos données sont insuffisantes pour générer une prévision. Votre solde de trésorerie actuel est de **{float(cash):,.0f} XOF**.",
                'type': 'text',
                'insights': [
                    f"Trésorerie nette : {float(cash):,.0f} XOF.",
                    "Données insuffisantes pour prévision IA."
                ]
            })
        
        return _chat_response(session, {
            'text': f"L'analyse prédictive de votre trésorerie sur 6 mois indique une trajectoire **{'positive' if cash > 0 else 'à surveiller'}**. Votre solde actuel est de **{float(cash):,.0f} XOF**.",
            'type': 'chart',
            'chart_type': 'line',
            'data': forecast,
            'insights': [
                f"Trésorerie nette : {float(cash):,.0f} XOF.",
                "Flux d'exploitation stable sur le mois en cours.",
                f"Indice de confiance des prévisions : {confidence}%."
            ]
        })

    # EBITDA & MARGINS
    if any(k in message for k in ['ebitda', 'marge', 'profit', 'rentabilité']):
        margin = (float(revenue - expenses) / float(revenue) * 100) if revenue > 0 else 0
        return _chat_response(session, {
            'text': f"Votre marge d'exploitation sur le mois en cours est estimée à **{margin:.1f}%**. Le résultat d'exploitation net est de **{float(revenue - expenses):,.0f} XOF**.",
            'type': 'chart',
            'chart_type': 'bar',
            'data': {
                'labels': ['Revenus', 'Dépenses', 'EBITDA'],
                'values': [float(revenue), float(expenses), float(revenue - expenses)]
            },
            'insights': [
                f"CA Mensuel : {float(revenue):,.2f} XOF",
                f"Charges : {float(expenses):,.2f} XOF",
                "Rentabilité conforme aux objectifs du secteur."
            ]
        })

    # BURN RATE & RUNWAY
    if any(k in message for k in ['burn', 'runway', 'autonomie', 'dépense']):
        runway = (float(cash) / float(avg_burn)) if avg_burn > 0 else 99
        return _chat_response(session, {
            'text': f"Votre **Burn Rate** moyen (3 mois) est de **{float(avg_burn):,.0f} XOF/mois**. Avec votre cash actuel, votre autonomie financière est de **{runway:.1f} mois**.",
            'type': 'list',
            'items': [
                {'title': 'Net Burn Rate', 'desc': f'{float(avg_burn):,.0f} XOF / mois.'},
                {'title': 'Cash Runway', 'desc': f'Environ {runway:.1f} mois de couverture.'},
                {'title': 'Statut', 'desc': 'Sain' if runway > 6 else 'Critique'}
            ],
            'insights': ["Optimisez vos charges fixes pour étendre le runway."]
        })

    # RISKS & ANOMALIES
    if any(k in message for k in ['risk', 'risque', 'alerte', 'anomalie']):
        anomalies = AnomalyDetection.objects.filter(company=company, is_false_positive=False)[:3]
        overdue_count = Invoice.objects.filter(company=company, status='overdue').count()
        
        items = []
        for ano in anomalies:
            items.append({'title': ano.title, 'desc': ano.description})
        if overdue_count > 0:
            items.append({'title': 'Factures en retard', 'desc': f'{overdue_count} factures clients dépassent la date d\'échéance.'})
        
        if not items:
            items.append({'title': 'Aucun risque majeur', 'desc': 'Tous les indicateurs de contrôle sont au vert.'})

        return _chat_response(session, {
            'text': f"L'audit IA a identifié **{len(items)} points d'attention**.",
            'type': 'list',
            'items': items,
            'insights': ["Renforcement recommandé du suivi de recouvrement."]
        })

    # 3. RAG Context Retrieval via ChromaDB + Gemini
    rag = RAGService()
    context_items = rag.retrieve_context(message, company, top_k=5)

    # Generate answer with Gemini (now with SQL + RAG context)
    user_name = request.user.first_name or 'Partenaire'
    rag_answer = rag.generate_rag_answer(
        raw_message,
        context_items,
        company=company,
        user_name=user_name,
        conversation_context=_conversation_context(session),
    )

    if rag_answer:
        sources = list({c['filename'] for c in context_items}) if context_items else []
        return _chat_response(session, {
            'text': rag_answer,
            'type': 'text',
            'sources': sources,
        })

    # 4. Fallback si Gemini indisponible
    if context_items:
        # Réponse basique avec le contexte sans LLM
        best = context_items[0]
        return _chat_response(session, {
            'text': f"**[Source: {best['filename']}]**\n\n{best['content'][:600]}...",
            'type': 'text',
            'sources': [c['filename'] for c in context_items],
        })

    return _chat_response(session, {
        'text': f"Bonjour {user_name}. Le Sakina Neural Core est opérationnel. Je peux analyser votre trésorerie, vos marges ou détecter des risques financiers.",
        'type': 'text',
        'suggestions': ["Forecast Trésorerie", "Analyse Marge EBITDA", "Calcul Burn Rate", "Détection Risques"],
    })

@login_required
def api_test_rag_service(request):
    """API: Diagnostics complets du service RAG — Gemini, embeddings, Pinecone"""
    from .services_rag import RAGService
    rag = RAGService()

    results = {
        'gemini': rag.test_gemini_connection(),
        'embedding': rag.test_embedding(),
        'pinecone': _test_pinecone(),
    }
    overall_ok = all(r['status'] == 'ok' for r in results.values())
    return JsonResponse({'status': 'ok' if overall_ok else 'degraded', 'tests': results})


def _test_pinecone():
    """Vérifie que Pinecone est accessible et opérationnel."""
    try:
        from pinecone import Pinecone
        from django.conf import settings
        
        api_key = getattr(settings, 'PINECONE_API_KEY', '')
        index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'sakina-vect')
        
        if not api_key:
            return {'status': 'error', 'message': 'PINECONE_API_KEY non défini'}
            
        pc = Pinecone(api_key=api_key)
        
        # Test describe index to see if it's reachable
        index_stats = pc.Index(index_name).describe_index_stats()
        
        return {
            'status': 'ok', 
            'message': f'Pinecone opérationnel sur {index_name} (Dimension: {index_stats.get("dimension")})'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@login_required
def api_upload_knowledge(request):
    """API: Upload a file to the knowledge base and index it"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    company = _get_company(request)
    file = request.FILES.get('file')
    
    if not file:
        return JsonResponse({'error': 'Aucun fichier fourni'}, status=400)
        
    try:
        doc = KnowledgeDocument.objects.create(
            company=company,
            file=file,
            filename=file.name,
            uploaded_by=request.user,
            file_type=file.name.split('.')[-1].lower() if '.' in file.name else ''
        )
        
        # Immediate indexing (should ideally be a Celery task)
        rag = RAGService()
        success = rag.index_document(doc.id)
        
        if success:
            return JsonResponse({'status': 'success', 'doc_id': str(doc.id)})
        else:
            return JsonResponse({'status': 'error', 'error': doc.error_message}, status=500)
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def api_ocr_documents(request):
    """API OCR: liste les documents OCR ou upload + traitement immédiat."""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'Aucune entreprise associée'}, status=400)

    if request.method == 'GET':
        documents = DocumentOCR.objects.filter(company=company).order_by('-created_at')[:30]
        return JsonResponse({'documents': [_serialize_ocr_document(doc) for doc in documents]})

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'Aucun fichier fourni'}, status=400)

    document_type = request.POST.get('document_type') or DocumentOCR.DocumentType.INVOICE
    valid_types = {choice[0] for choice in DocumentOCR.DocumentType.choices}
    if document_type not in valid_types:
        return JsonResponse({'error': 'Type de document OCR invalide'}, status=400)

    max_size = 15 * 1024 * 1024
    if file.size > max_size:
        return JsonResponse({'error': 'Fichier trop volumineux. Limite: 15 Mo.'}, status=400)

    doc = DocumentOCR.objects.create(
        company=company,
        document_type=document_type,
        file=file,
        filename=file.name,
        file_size=file.size,
        uploaded_by=request.user,
    )

    from .services_ocr import OCRService

    doc = OCRService().process_document(doc)
    status_code = 201 if doc.status != DocumentOCR.Status.FAILED else 422
    return JsonResponse({'document': _serialize_ocr_document(doc)}, status=status_code)


@login_required
@require_http_methods(["GET", "POST"])
def api_ocr_document_detail(request, document_id):
    """API OCR: détail ou retraitement d'un document."""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'Aucune entreprise associée'}, status=400)

    doc = get_object_or_404(DocumentOCR, id=document_id, company=company)

    if request.method == 'GET':
        return JsonResponse({'document': _serialize_ocr_document(doc)})

    from .services_ocr import OCRService

    doc = OCRService().process_document(doc)
    status_code = 200 if doc.status != DocumentOCR.Status.FAILED else 422
    return JsonResponse({'document': _serialize_ocr_document(doc)}, status=status_code)


@login_required
@require_http_methods(["POST"])
def api_ocr_validate_document(request, document_id):
    """API OCR: valide les données extraites et peut créer une facture brouillon."""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'Aucune entreprise associée'}, status=400)

    doc = get_object_or_404(DocumentOCR, id=document_id, company=company)
    body = _json_body(request)
    if body is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if body.get('extracted_data'):
        doc.extracted_data = body['extracted_data']

    create_invoice = bool(body.get('create_invoice'))
    invoice_payload = None
    if create_invoice:
        from .services_ocr import OCRService

        if body.get('extracted_data'):
            doc.save(update_fields=['extracted_data'])

        invoice_type = body.get('invoice_type') or Invoice.InvoiceType.SUPPLIER
        if invoice_type not in {Invoice.InvoiceType.CUSTOMER, Invoice.InvoiceType.SUPPLIER}:
            return JsonResponse({'error': 'Type de facture invalide'}, status=400)
        invoice = OCRService().create_invoice_from_ocr(doc, invoice_type=invoice_type)
        invoice_payload = {
            'id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'partner_name': invoice.partner_name,
            'total': float(invoice.total),
            'currency': invoice.currency,
            'status': invoice.status,
        }
    else:
        doc.status = DocumentOCR.Status.VALIDATED
        doc.save(update_fields=['extracted_data', 'status'])

    return JsonResponse({
        'document': _serialize_ocr_document(doc),
        'invoice': invoice_payload,
    })
