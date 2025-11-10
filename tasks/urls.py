
from django.urls import path, include 
from rest_framework.permissions import AllowAny
from .views import ReportView
from .views import (
    LoginView, 
    UserView,
    SuperManagerDashboardStats,
    SuperManagerUserViewSet,
    SuperManagerProjectViewSet,
    SuperManagerTaskViewSet,
    RecentActivityView,
    ManagerProjectViewSet,  # Add this import
    ManagerTaskViewSet,     # Add this import
    ManagerEmployeeListView ,
     ManagerDashboardStats,
     EmployeeTaskViewSet,
     
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'supermanager/users', SuperManagerUserViewSet, basename='supermanager-users')
router.register(r'supermanager/projects', SuperManagerProjectViewSet, basename='supermanager-projects')
router.register(r'supermanager/tasks', SuperManagerTaskViewSet, basename='supermanager-tasks')
router.register(r'manager/projects', ManagerProjectViewSet, basename='manager-projects')
router.register(r'manager/tasks', ManagerTaskViewSet, basename='manager-tasks')
router.register(r'employee/tasks', EmployeeTaskViewSet, basename='employee-tasks')



urlpatterns = [
    path('login/', LoginView.as_view(permission_classes=[AllowAny]), name='login'),
    path('user/', UserView.as_view(), name='user'),
    path('supermanager-dashboard-stats/', SuperManagerDashboardStats.as_view(), name='supermanager-dashboard-stats'),
     path('manager/employees/', ManagerEmployeeListView.as_view(), name='manager-employees'),
      path('manager-dashboard-stats/', ManagerDashboardStats.as_view(), name='manager-dashboard-stats'),
    path('recent-activity/', RecentActivityView.as_view(), name='recent-activity'),
    path('reports/', ReportView.as_view(), name='reports'),
    path('', include(router.urls)),
]
# urls.py
# from django.urls import path, include
# from rest_framework.permissions import AllowAny
# from rest_framework.routers import DefaultRouter
# from .views import (
#     LoginView,
#     UserView,
#     SuperManagerDashboardStats,
#     SuperManagerUserViewSet,
#     SuperManagerProjectViewSet,
#     SuperManagerTaskViewSet,
#     RecentActivityView,
#     ReportView,
#     ManagerDashboardStats,
#     ManagerProjectViewSet,
#     ManagerTaskViewSet,
#     ActivitySerializer  # Remove ActivityViewSet from here if not needed
# )

# router = DefaultRouter()

# # Super Manager routes
# router.register(r'supermanager/users', SuperManagerUserViewSet, basename='supermanager-users')
# router.register(r'supermanager/projects', SuperManagerProjectViewSet, basename='supermanager-projects')
# router.register(r'supermanager/tasks', SuperManagerTaskViewSet, basename='supermanager-tasks')

# # Manager routes
# router.register(r'manager/projects', ManagerProjectViewSet, basename='manager-projects')
# router.register(r'manager/tasks', ManagerTaskViewSet, basename='manager-tasks')

# urlpatterns = [
#     # Authentication
#     path('login/', LoginView.as_view(permission_classes=[AllowAny]), name='login'),
#     path('user/', UserView.as_view(), name='user'),
    
#     # Dashboard stats
#     path('supermanager-dashboard-stats/', SuperManagerDashboardStats.as_view(), name='supermanager-dashboard-stats'),
#     path('manager-dashboard-stats/', ManagerDashboardStats.as_view(), name='manager-dashboard-stats'),
    
#     # Activity and reports
#     path('recent-activity/', RecentActivityView.as_view(), name='recent-activity'),
#     path('reports/', ReportView.as_view(), name='reports'),
    
#     # Include all router URLs
#     path('', include(router.urls)),
# ]