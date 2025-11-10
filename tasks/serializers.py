
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework.fields import DateField, DateTimeField
from .models import CustomUser, Project, Task, Activity  

# class UserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=False)
#     date_joined = DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
#     confirmPassword = serializers.CharField(write_only=True, required=False)

#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'username', 'email', 'full_name', 'role', 
#             'password', 'confirmPassword', 'is_active', 'date_joined'
#         ]
#         extra_kwargs = {
#             'username': {'required': True},
#             'email': {'required': True},
#         }

#     def validate(self, data):
#         if 'password' in data:
#             if len(data['password']) < 8:
#                 raise serializers.ValidationError({"password": "Password must be at least 8 characters"})
#                 if data.get('password') != data.get('confirmPassword'):
#                     raise serializers.ValidationError({"password": "Password fields didn't match."})
#         return data

#     def create(self, validated_data):
#         password = validated_data.pop('password')
#         validated_data.pop('confirmPassword', None)
#         user = CustomUser(**validated_data)
#         user.set_password(password)
#         user.save()
#         return user

#     def update(self, instance, validated_data):
#         validated_data.pop('confirmPassword', None)
#         password = validated_data.pop('password', None)
        
#         if password:
#             instance.set_password(password)
        
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
        
#         instance.save()
#         return instance
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    date_joined = DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    confirmPassword = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'full_name', 'role', 
            'password', 'confirmPassword', 'is_active', 'date_joined'
        ]
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
        }

    def validate(self, data):
        if 'password' in data:
            if len(data['password']) < 8:
                raise serializers.ValidationError({"password": "Password must be at least 8 characters"})
            if data.get('password') != data.get('confirmPassword'):
                raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('confirmPassword', None)
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop('confirmPassword', None)
        password = validated_data.pop('password', None)
        
        if password:
            instance.set_password(password)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                data['user'] = user
            else:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")
        return data

# serializers.py
class ProjectSerializer(serializers.ModelSerializer):
    created_at = DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    deadline = DateField(format="%Y-%m-%d", required=False, allow_null=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='manager'),
        required=True
    )

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_by', 'assigned_to', 'created_at', 'deadline']
        read_only_fields = ['created_by', 'created_at']

    def validate_assigned_to(self, value):
        if value.role != 'manager':
            raise serializers.ValidationError("The assigned user must be a manager")
        return value


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='employee'),
        required=True
    )
    assigned_by = serializers.StringRelatedField(read_only=True)
    created_at = DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    due_date = DateField(format="%Y-%m-%d", required=False, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)
    display_status = serializers.SerializerMethodField()
    assigned_to_details = serializers.SerializerMethodField()
    assigned_by_details = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)  
    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        if 'assigned_to' in data and data['assigned_to']:
            if data['assigned_to'].role != 'employee':
                raise serializers.ValidationError(
                    {"assigned_to": "Must assign to an employee"}
                )
        return data

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('assigned_by', 'created_at', 'is_overdue')

    def get_display_status(self, obj):
        if obj.is_overdue:
            return "Overdue"
        return obj.get_status_display()

    def get_assigned_to_details(self, obj):
        if obj.assigned_to:
            return {
                'id': obj.assigned_to.id,
                'username': obj.assigned_to.username,
                'full_name': obj.assigned_to.full_name,
                'email': obj.assigned_to.email
            }
        return None

    def get_assigned_by_details(self, obj):
        if obj.assigned_by:
            return {
                'id': obj.assigned_by.id,
                'username': obj.assigned_by.username,
                'full_name': obj.assigned_by.full_name
            }
        return None
class RecentActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    timestamp = DateTimeField(format="%Y-%m-%d %H:%M:%S")
    user = serializers.CharField()
    user_role = serializers.CharField()
    status = serializers.CharField(required=False)
    action = serializers.CharField()
class ActivitySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = Activity
        fields = ['id', 'user', 'user_role', 'action', 'content_type', 'object_id', 'details', 'timestamp']




class ManagerProjectSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'deadline', 'progress', 'total_tasks', 'completed_tasks']

    def get_progress(self, obj):
        tasks = obj.tasks.all()
        total = tasks.count()
        completed = tasks.filter(status='completed').count()
        return round((completed / total) * 100) if total > 0 else 0

    def get_total_tasks(self, obj):
        return obj.tasks.count()

    def get_completed_tasks(self, obj):
        return obj.tasks.filter(status='completed').count()