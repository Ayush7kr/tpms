from django.urls import path
from apps.career_assistant import views

app_name = 'career_assistant'

urlpatterns = [
    path('', views.career_assistant_view, name='career_assistant'),
    path('c/<int:conversation_id>/', views.career_assistant_view, name='career_assistant_detail'),
    path('api/chat/', views.chat_api_view, name='chat_api'),
    path('api/new/', views.conversation_create_view, name='new_conversation'),
    path('api/clear/<int:conversation_id>/', views.conversation_clear_view, name='clear_conversation'),
    path('api/delete/<int:conversation_id>/', views.conversation_delete_view, name='delete_conversation'),
]
