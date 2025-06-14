from . import views
from django.urls import path, include

from .views import *

app_name='chatbot'
urlpatterns=[
    # path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('', views.home_view, name='home'),
    path('chat-response/', views.chat_response, name='chat_response'),
    path('get_chat_sessions/', views.get_chat_sessions, name='get_chat_sessions'),
    path('get_session_messages/<uuid:session_id>/', views.get_session_messages, name='get_session_messages'),
    path('create_chat_session/', views.create_chat_session, name='create_chat_session'),
    path('delete_chat_session/<uuid:session_id>/', views.delete_chat_session, name='delete_chat_session'),
]
