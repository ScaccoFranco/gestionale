from rest_framework import serializers
from .models import Ticket, TicketComment

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'ticket_type', 'priority', 'status',
            'user', 'user_email', 'page_url', 'user_agent', 'browser_info',
            'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'resolved_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
            validated_data['user_email'] = request.user.email
        return super().create(validated_data)

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            'title', 'description', 'ticket_type', 'priority',
            'page_url', 'user_agent', 'browser_info'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
            validated_data['user_email'] = request.user.email
        elif request and hasattr(request, 'data'):
            validated_data['user_email'] = request.data.get('user_email')
        return super().create(validated_data)

class TicketCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.CharField(source='author.email', read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'author', 'author_email', 'comment', 'is_internal', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']