
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Q, Count, F, Case, When, FloatField
from django.db.models.functions import Coalesce
from .models import CustomUser, Project, Task
from .serializers import UserSerializer, ProjectSerializer, TaskSerializer
from django.db.models.functions import TruncDate
from rest_framework import generics  # Add this import
class SuperManagerDashboardStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'supermanager':
            return Response({'error': 'Unauthorized'}, status=403)

        stats = {
            'total_users': CustomUser.objects.count(),
            'active_projects': Project.objects.count(),
            'pending_tasks': Task.objects.filter(status='pending').count(),
            'in_progress_tasks': Task.objects.filter(status='in_progress').count(),
            'completed_tasks': Task.objects.filter(status='completed').count()
        }
        return Response(stats)


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class SuperManagerUserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'supermanager':
            return CustomUser.objects.all().order_by('-date_joined')  # Newest first
        return CustomUser.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # For the dashboard, return only active users
        if request.query_params.get('dashboard') == 'true':
            queryset = queryset.filter(is_active=True)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SuperManagerProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            # Ensure the request user is a supermanager
            if request.user.role != 'supermanager':
                return Response(
                    {'message': 'Only supermanagers can create projects'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Set the created_by field to the current user
            serializer.save(created_by=request.user)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )



class SuperManagerTaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'supermanager':
            return Task.objects.none()
            
        queryset = Task.objects.select_related(
            'assigned_to', 'assigned_by', 'project'
        ).order_by('-created_at')
        
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class RecentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get limit parameter from request, default to 10
        limit = int(request.GET.get('limit', 10))
        
        # Get tasks, projects, and users that were updated or created recently
        task_qs = Task.objects.filter(
            Q(created_at__gte=now() - timedelta(days=30)) | 
            Q(updated_at__gte=now() - timedelta(days=30))
        ).select_related('assigned_by', 'assigned_to', 'project')

        project_qs = Project.objects.filter(
            Q(created_at__gte=now() - timedelta(days=30)) | 
            Q(updated_at__gte=now() - timedelta(days=30))
        ).select_related('created_by')

        # Get recently created users
        user_qs = CustomUser.objects.filter(
            date_joined__gte=now() - timedelta(days=30)
        )

        activities = []

        # Process tasks - CRITICAL: Show task completion as manager's action
        for task in task_qs:
            # For task creation
            if task.created_at >= now() - timedelta(days=1):  # Created recently
                activities.append({
                    "id": f"task_{task.id}_created",
                    "type": "task",
                    "title": f"Task created: {task.title}",
                    "description": f"Assigned to {task.assigned_to.full_name or task.assigned_to.username}",
                    "timestamp": task.created_at,
                    "user": task.assigned_by.full_name or task.assigned_by.username,
                    "user_role": task.assigned_by.role,
                    "status": task.status,
                    "action": "created",
                    "task_title": task.title,
                    "project_name": task.project.name if task.project else "No Project",
                    "assigned_to": task.assigned_to.full_name or task.assigned_to.username
                })
            
            # For task completion - ATTRIBUTE TO MANAGER, not employee
            if (task.status == 'completed' and 
                task.updated_at >= now() - timedelta(days=1) and
                task.updated_at != task.created_at):  # Ensure it was updated after creation
                
                activities.append({
                    "id": f"task_{task.id}_completed",
                    "type": "task",
                    "title": f"Task completed: {task.title}",
                    "description": f"Completed by team under {task.assigned_by.full_name or task.assigned_by.username}",
                    "timestamp": task.updated_at,
                    "user": task.assigned_by.full_name or task.assigned_by.username,  # Show MANAGER, not employee
                    "user_role": task.assigned_by.role,  # Manager's role
                    "status": "completed",
                    "action": "completed",
                    "task_title": task.title,
                    "project_name": task.project.name if task.project else "No Project",
                    "completed_by": task.assigned_to.full_name or task.assigned_to.username  # Optional: show who executed
                })

        # Process projects
        for project in project_qs:
            action = "updated" if project.updated_at != project.created_at else "created"
            activities.append({
                "id": f"project_{project.id}",
                "type": "project",
                "title": f"Project {action}: {project.name}",
                "description": project.description,
                "timestamp": project.updated_at if action == "updated" else project.created_at,
                "user": project.created_by.full_name or project.created_by.username,
                "user_role": project.created_by.role,
                "status": "active",
                "action": action,
                "project_name": project.name
            })

        # Process user creation
        for user in user_qs:
            activities.append({
                "id": f"user_{user.id}",
                "type": "user",
                "title": f"User created: {user.full_name or user.username}",
                "description": f"New {user.role} account created",
                "timestamp": user.date_joined,
                "user": "System",
                "user_role": "supermanager",
                "status": "active" if user.is_active else "inactive",
                "action": "created",
                "target_user": user.full_name or user.username,
                "user_role_created": user.role
            })

        # Sort by timestamp descending and apply limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response(activities[:limit])

class ReportView(APIView):
    def get(self, request):
        project_id = request.query_params.get('project')
        
        # Get all projects for the filter dropdown
        all_projects = Project.objects.all()
        
        # Base queryset with optional project filter
        tasks_queryset = Task.objects.all()
        if project_id:
            tasks_queryset = tasks_queryset.filter(project_id=project_id)
        
        # Calculate basic statistics
        total_tasks = tasks_queryset.count()
        completed_tasks = tasks_queryset.filter(status='completed').count()
        pending_tasks = tasks_queryset.filter(status='pending').count()
        in_progress_tasks = tasks_queryset.filter(status='in_progress').count()
        overdue_tasks = tasks_queryset.filter(
            Q(due_date__lt=timezone.now().date()) & 
            ~Q(status='completed')
        ).count()
        
        # Status distribution for chart
        status_labels = ['Pending', 'In Progress', 'Completed', 'Overdue']
        status_data = [
            pending_tasks,
            in_progress_tasks,
            completed_tasks,
            overdue_tasks
        ]
        
        # Projects progress
        projects_queryset = Project.objects.all()
        if project_id:
            projects_queryset = projects_queryset.filter(id=project_id)
            
        projects_progress = []
        for project in projects_queryset:
            project_tasks = project.tasks.all()
            total = project_tasks.count()
            completed = project_tasks.filter(status='completed').count()
            
            progress = 0
            if total > 0:
                progress = (completed / total) * 100
                
            projects_progress.append({
                'id': project.id,
                'name': project.name,
                'progress': progress,
                'total_tasks': total,
                'completed_tasks': completed
            })
        
        response_data = {
            'stats': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'in_progress_tasks': in_progress_tasks,
                'overdue_tasks': overdue_tasks,
            },
            'statusDistribution': {
                'labels': status_labels,
                'data': status_data
            },
            'projectsProgress': projects_progress,
            'allProjects': [{'id': p.id, 'name': p.name} for p in all_projects],
        }
        
        return Response(response_data)
class ManagerProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'manager':
            return Project.objects.filter(assigned_to=self.request.user)
        return Project.objects.none()
# In views.py
class ManagerTaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'manager':
            project_id = self.request.query_params.get('project')
            
            # If project ID is provided, verify it belongs to this manager
            if project_id:
                if not Project.objects.filter(
                    id=project_id, 
                    assigned_to=self.request.user
                ).exists():
                    return Task.objects.none()
                return Task.objects.filter(project_id=project_id)
            
            # If no project specified, return all tasks for manager's projects
            manager_projects = Project.objects.filter(assigned_to=self.request.user)
            return Task.objects.filter(project__in=manager_projects)
        return Task.objects.none()
# class ManagerTaskViewSet(viewsets.ModelViewSet):
#     serializer_class = TaskSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         if self.request.user.role == 'manager':
#             # Get tasks from projects assigned to this manager
#             manager_projects = Project.objects.filter(assigned_to=self.request.user)
#             return Task.objects.filter(project__in=manager_projects)
#         return Task.objects.none()

#     def perform_create(self, serializer):
#         serializer.save(assigned_by=self.request.user)

class ManagerEmployeeListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'manager':
            return CustomUser.objects.filter(role='employee')
        return CustomUser.objects.none()
class ManagerDashboardStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'manager':
            return Response({'error': 'Unauthorized'}, status=403)

        projects = Project.objects.filter(assigned_to=request.user)
        project_ids = projects.values_list('id', flat=True)
        tasks = Task.objects.filter(project__in=project_ids)

        stats = {
            'total_projects': projects.count(),
            'active_projects': projects.filter(deadline__gte=timezone.now()).count(),
            'pending_tasks': tasks.filter(status='pending').count(),
            'in_progress_tasks': tasks.filter(status='in_progress').count(),
            'completed_tasks': tasks.filter(status='completed').count(),
            'overdue_tasks': tasks.filter(
                Q(due_date__lt=timezone.now().date()) & ~Q(status='completed')
            ).count()
        }

        return Response(stats)
# views.py
class EmployeeTaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'employee':
            return Task.objects.filter(assigned_to=self.request.user)
        return Task.objects.none()

    def perform_create(self, serializer):
        # Employees shouldn't be able to assign tasks to others
        serializer.save(assigned_to=self.request.user)
