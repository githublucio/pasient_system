from django.urls import path
from . import views
from . import rbac_views

urlpatterns = [
    path('logout/', views.custom_logout, name='logout_custom'),
    # Department URLs
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/add/', views.DepartmentCreateView.as_view(), name='department_add'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_edit'),
    path('departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),

    # Category URLs
    path('categories/', views.StaffCategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.StaffCategoryCreateView.as_view(), name='category_add'),

    # Position URLs
    path('positions/', views.PositionListView.as_view(), name='position_list'),
    path('positions/add/', views.PositionCreateView.as_view(), name='position_add'),

    # Staff Profile URLs
    path('', views.StaffListView.as_view(), name='staff_list'),
    path('add/', views.StaffCreateView.as_view(), name='staff_add'),
    path('<int:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_edit'),

    # RBAC Role Permission Manager
    path('rbac/', rbac_views.RolePermissionMatrixView.as_view(), name='role_permissions'),
    path('rbac/<int:group_id>/', rbac_views.RolePermissionMatrixView.as_view(), name='role_permissions_selected'),
    path('rbac/<int:group_id>/save/', rbac_views.RolePermissionMatrixView.as_view(), name='role_permissions_save'),
    
    # Role CRUD
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/add/', views.RoleCreateView.as_view(), name='role_add'),
    path('roles/<int:pk>/edit/', views.RoleUpdateView.as_view(), name='role_edit'),
    path('roles/<int:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),
    
    # User Role Assignment
    path('rbac/user-roles/', rbac_views.UserRoleMapperView.as_view(), name='user_role_assignment'),
]
