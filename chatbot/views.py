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
# Create your views here.
login_required()
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login(request, user)  # Automatically log the user in after registration
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('chatbot:login')  # Replace 'home' with the desired redirect path
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})

# Login View
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

# Logout View
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('chatbot:login')  # Replace 'login' with the login page URL name

@login_required
def chatbot_view(request):
    return render(request,'chatbot.html')


def home_view(request):
    return redirect('chatbot:chatbot')  

# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatMessage
from .services.chatgpt_service import ChatGPTService
import json

chatgpt_service = ChatGPTService()
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services.chatgpt_service import ChatGPTService
import json
# import logging

# Set up logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

chatgpt_service = ChatGPTService()

@login_required
@csrf_exempt
def chat_response(request):
    if request.method == 'POST':
        try:
            # Log the incoming request
            # logger.debug("Received chat request")
            
            data = json.loads(request.body)
            user_query = data.get('message', '')
            
            # logger.debug(f"User Query: {user_query}")

            # Step 1: Analyze query with ChatGPT
            try:
                response_text = chatgpt_service.analyze_query(user_query)
                # logger.debug(f"Medical ter
                # ms found: {medical_terms if has_medical_terms else 'None'}")
            except Exception as e:
                print(e)
                # logger.error(f"Error in analyze_query: {str(e)}")
                raise

            # response_text = None

            # if has_medical_terms:
            #     # Step 2: Search PubMed if medical terms found
            #     try:
            #         research_papers = pubmed_service.search_papers(medical_terms)
            #         logger.debug(f"Research papers found: {'Yes' if research_papers else 'No'}")
            #     except Exception as e:
            #         logger.error(f"Error in PubMed search: {str(e)}")
            #         research_papers = None

            #     # Step 3: Generate response
            #     try:
            #         if research_papers:
            #             response_text = chatgpt_service.generate_response(user_query, research_papers)
            #         else:
            #             response_text = chatgpt_service.generate_response(user_query)
            #     except Exception as e:
            #         logger.error(f"Error in generate_response: {str(e)}")
            #         raise
            # else:
            #     response_text = chatgpt_service.generate_response(user_query)

            # if not response_text:
            #     raise Exception("No response generated")

            # logger.debug(f"Response generated successfully: {response_text[:100]}...")

            return JsonResponse({
                'status': 'success',
                'response': response_text
            })

        except Exception as e:
            # logger.error(f"Error processing request: {str(e)}")
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
    # Simple response logic (replace with your chatbot logic)
    message = message.lower()
    
    if 'hello' in message:
        return "Hello! How can I help you today?"
    elif 'appointment' in message:
        return "Would you like to schedule an appointment? Please let me know your preferred date and time."
    elif 'emergency' in message:
        return "If this is a medical emergency, please call emergency services immediately at 911."
    else:
        return "I understand. How else can I assist you?"