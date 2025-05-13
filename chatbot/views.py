from django.shortcuts import render
from .forms import RegisterForm, LoginForm
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ChatMessage
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .services.chatgpt_service import ChatGPTService

chatgpt_service = ChatGPTService()

@login_required
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
def chat_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('message', '')
            # Retrieve or initialize conversation history from session
            session_key = f'chat_history_{request.user.id}'
            chat_history = request.session.get(session_key, [])
            # Append current user query
            chat_history.append({"role": "user", "content": user_query})
            # Limit history to last 10 messages to avoid token overflow
            chat_history = chat_history[-15:]
            # Analyze query with history
            response_text = chatgpt_service.analyze_query(user_query, chat_history)
            # Append bot response to history
            chat_history.append({"role": "assistant", "content": response_text})
            # Save updated history
            request.session[session_key] = chat_history
            return JsonResponse({
                'status': 'success',
                'response': response_text
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