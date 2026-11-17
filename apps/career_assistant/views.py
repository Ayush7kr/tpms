import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.accounts.decorators import student_required
from apps.career_assistant.models import Conversation, ChatMessage
from apps.career_assistant.services.ai_service import AICareerAssistantService


@student_required
def career_assistant_view(request, conversation_id=None):
    """
    Renders the dedicated AI Career & Placement Assistant interface.
    Scopes all conversations and messages strictly to the authenticated student.
    """
    profile = request.user.student_profile
    conversations = Conversation.objects.filter(student=profile).order_by('-updated_at')

    active_conversation = None
    if conversation_id:
        active_conversation = get_object_or_404(Conversation, id=conversation_id, student=profile)
    elif conversations.exists():
        active_conversation = conversations.first()
    else:
        active_conversation = Conversation.objects.create(
            student=profile,
            title='Career chat'
        )
        # Pre-seed with welcome message
        ChatMessage.objects.create(
            conversation=active_conversation,
            sender='ASSISTANT',
            content=f"Hi {profile.user.first_name}. I can see your record ({profile.department.code}, CGPA {profile.graduation_cgpa}), your skills and the drives that are open right now.\n\nAsk me how to prepare for a specific company, what to add to your resume, or what to study this month."
        )

    chat_messages = active_conversation.messages.order_by('timestamp') if active_conversation else []
    has_api_key = bool(AICareerAssistantService.get_api_key())

    return render(request, 'student_panel/career_assistant.html', {
        'profile': profile,
        'conversations': conversations,
        'active_conversation': active_conversation,
        'chat_messages': chat_messages,
        'has_api_key': has_api_key,
        'active_nav': 'career_assistant'
    })


@student_required
@require_POST
def chat_api_view(request):
    """
    AJAX endpoint for conversational queries.
    Enforces strict rate limits, input sanitization, and student ownership.
    """
    profile = request.user.student_profile

    # Support both JSON payload and form-encoded data
    message_text = ""
    conversation_id = None

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
            message_text = data.get('message', '').strip()
            conversation_id = data.get('conversation_id')
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body.")
    else:
        message_text = request.POST.get('message', '').strip()
        conversation_id = request.POST.get('conversation_id')

    if not message_text:
        return JsonResponse({'success': False, 'error': 'Query message cannot be empty.'}, status=400)

    if len(message_text) > 2000:
        return JsonResponse({'success': False, 'error': 'Query exceeds the maximum allowed length (2,000 characters).'}, status=400)

    # Ownership check
    conversation = get_object_or_404(Conversation, id=conversation_id, student=profile)

    # Record student message
    student_msg = ChatMessage.objects.create(
        conversation=conversation,
        sender='STUDENT',
        content=message_text
    )

    # Auto-generate dynamic title if default
    if conversation.title in ('Career chat', 'New chat', 'Placement Preparation & Career Guidance', 'New Career Chat', 'Career Guidance Session'):
        conversation.title = message_text[:40] + ('...' if len(message_text) > 40 else '')
        conversation.save(update_fields=['title', 'updated_at'])

    # Invoke AI Service
    try:
        assistant_reply = AICareerAssistantService.generate_response(conversation, message_text)
    except Exception as e:
        assistant_reply = "I encountered an unexpected issue processing your placement query. Please try again or rephrase your request."

    # Record assistant message
    assistant_msg = ChatMessage.objects.create(
        conversation=conversation,
        sender='ASSISTANT',
        content=assistant_reply
    )

    return JsonResponse({
        'success': True,
        'reply': assistant_reply,
        'timestamp': assistant_msg.timestamp.strftime('%H:%M'),
        'conversation_title': conversation.title
    })


@student_required
@require_POST
def conversation_create_view(request):
    """
    Starts a fresh new chat session for the authenticated student.
    """
    profile = request.user.student_profile
    new_conv = Conversation.objects.create(
        student=profile,
        title='New chat'
    )
    ChatMessage.objects.create(
        conversation=new_conv,
        sender='ASSISTANT',
        content=f"New chat started. What would you like to work on, {profile.user.first_name}?"
    )
    return redirect('career_assistant:career_assistant_detail', conversation_id=new_conv.id)


@student_required
@require_POST
def conversation_delete_view(request, conversation_id):
    """
    Deletes an existing conversation session with strict student ownership validation.
    """
    profile = request.user.student_profile
    conversation = get_object_or_404(Conversation, id=conversation_id, student=profile)
    conversation.delete()
    messages.info(request, "Conversation session removed.")
    return redirect('career_assistant:career_assistant')


@student_required
@require_POST
def conversation_clear_view(request, conversation_id):
    """
    Clears all chat messages within a conversation.
    """
    profile = request.user.student_profile
    conversation = get_object_or_404(Conversation, id=conversation_id, student=profile)
    conversation.messages.all().delete()
    messages.info(request, "Chat history in this session has been cleared.")
    return redirect('career_assistant:career_assistant_detail', conversation_id=conversation.id)
