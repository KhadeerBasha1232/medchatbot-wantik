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
    
]
