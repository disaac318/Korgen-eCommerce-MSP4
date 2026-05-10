from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    path('password-reset/', views.password_reset_request, name='password_reset'),
    path(
        'password-reset/<uidb64>/<token>/',
        views.password_reset_confirm,
        name='password_reset_confirm',
    ),
]
