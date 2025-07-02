from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .forms import RegisterForm, LoginForm
from .models import ChatSession, ChatMessage
from .services.chatgpt_service import ChatGPTService
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
import uuid

chatgpt_service = ChatGPTService()
executor = ThreadPoolExecutor(max_workers=4)

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('chatbot:login')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful.')
                return redirect('chatbot:chatbot')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('chatbot:login')

@login_required
def chatbot_view(request):
    return render(request, 'chatbot.html')

def home_view(request):
    return redirect('chatbot:chatbot')

@login_required
@csrf_exempt
def create_chat_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title', 'New Chat')
            session = ChatSession.objects.create(
                user=request.user,
                session_id=str(uuid.uuid4()),
                title=title
            )
            return JsonResponse({
                'status': 'success',
                'session_id': str(session.session_id),
                'title': session.title
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST method is allowed'
    }, status=405)

@login_required
@csrf_exempt
def chat_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('message', '')
            session_id = data.get('session_id', str(uuid.uuid4()))  # Use provided session_id or create new
            # Get or create chat session
            session, created = ChatSession.objects.get_or_create(
                user=request.user,
                session_id=session_id,
                defaults={'title': 'New Chat'}  # Default title, will update below if first message
            )
            # Check if this is the first message in the session
            if created or session.messages.count() == 0:
                # Update session title to first 50 characters of the query (or entire query if shorter)
                session.title = user_query[:50] + "..." if len(user_query) > 50 else user_query
                session.save()
            # Retrieve session chat history (properly interleaved)
            chat_history = []
            messages = session.messages.all().order_by('created_at')
            for msg in messages:
                chat_history.append({"role": "user", "content": msg.message})
                chat_history.append({"role": "assistant", "content": msg.response})
            
            print(f"Chat history for session {session.session_id}: {chat_history}")
            
            # Limit to last 4 exchanges (8 messages) to avoid token limits
            chat_history = chat_history[-8:]
            # Get response from ChatGPTService
            response_text = executor.submit(
                partial(chatgpt_service.analyze_query, user_query, chat_history)
            ).result()
            # Save message to database
            ChatMessage.objects.create(
                user=request.user,
                session=session,
                message=user_query,
                response=response_text
            )
            return JsonResponse({
                'status': 'success',
                'response': response_text,
                'session_id': str(session.session_id),
                'title': session.title  # Include updated title in response
            })
        except Exception as e:
            print(e)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST method is allowed'
    }, status=405)

@login_required
def get_chat_sessions(request):
    if request.method == 'GET':
        try:
            sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
            sessions_data = [
                {
                    'session_id': str(session.session_id),
                    'title': session.title,
                    'created_at': session.created_at.isoformat()
                }
                for session in sessions
            ]
            return JsonResponse({
                'status': 'success',
                'sessions': sessions_data
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Only GET method is allowed'
    }, status=405)

@login_required
def get_session_messages(request, session_id):
    if request.method == 'GET':
        try:
            session = ChatSession.objects.get(user=request.user, session_id=session_id)
            messages = session.messages.all()
            messages_data = [
                {
                    'role': 'user',
                    'content': msg.message,
                    'created_at': msg.created_at.isoformat()
                } for msg in messages
            ] + [
                {
                    'role': 'assistant',
                    'content': msg.response,
                    'created_at': msg.created_at.isoformat()
                } for msg in messages
            ]
            messages_data.sort(key=lambda x: x['created_at'])
            return JsonResponse({
                'status': 'success',
                'messages': messages_data,
                'session_id': str(session.session_id),
                'title': session.title
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Session not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Only GET method is allowed'
    }, status=405)


@login_required
@csrf_exempt
def delete_chat_session(request, session_id):
    if request.method == 'DELETE':
        try:
            session = ChatSession.objects.get(user=request.user, session_id=session_id)
            session.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Session deleted successfully'
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Session not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Only DELETE method is allowed'
    }, status=405)

def generate_bot_response(message):
    message = message.lower()
    if 'hello' in message:
        return "Hello! How can I help you today?"
    elif 'appointment' in message:
        return "Would you like to schedule an appointment? Please let me know your preferred date and time."
    elif 'emergency' in message:
        return "If this is a medical emergency, please call emergency services immediately at 911."
    else:
        return "I understand. How else can I assist you?"