# chatbot/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)  # Auto-generated from first message
    created_at = models.DateTimeField(auto_now_add=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.title:
            # Set default title based on first message or timestamp
            first_message = self.messages.first()
            if first_message:
                self.title = first_message.message[:50] + "..." if len(first_message.message) > 50 else first_message.message
            else:
                self.title = f"Chat {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        super().save(*args, **kwargs)

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']