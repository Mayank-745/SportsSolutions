from portal import views
from django.urls import path

urlpatterns = [
    path('', views.home, name = "home"),
    path('lms/', views.lms, name = "lms"),
    path('sign/', views.sign, name = "sign"),
    path('login/', views.log_in, name = "login"),
    path('portal/', views.portal, name = "portal"),
    path('register/', views.register, name = "register"),
    path('event1/', views.event1, name = "event1"),
    path('create-order/', views.create_order, name='create_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'), 
]
