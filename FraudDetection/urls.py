from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from FraudDetection import views as mainView
from users import views as usr
from admins import views as admins

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", mainView.index, name='index'),
    path("index", mainView.index, name="index"),
    path("logout", mainView.logout, name="logout"),
    path("UserLogin", mainView.UserLogin, name="UserLogin"),
    path("AdminLogin", mainView.AdminLogin, name="AdminLogin"),
    path("UserRegister", mainView.UserRegister, name="UserRegister"),

    path("UserRegisterActions", usr.UserRegisterActions, name="UserRegisterActions"),
    path("UserLoginCheck", usr.UserLoginCheck, name="UserLoginCheck"),
    path("User_Home", usr.UserHome, name="User_Home"),
    
    path('video_feed/', usr.video_feed, name='video_feed'),
    path('get_abnormal_status/', usr.get_abnormal_status, name='get_abnormal_status'),
    path("predict_image", usr.predict_image, name="predict_image"),
    path('logout_views',usr.logout_views,name='logout_views'),

    path("AdminLoginCheck", admins.AdminLoginCheck, name="AdminLoginCheck"),
    path("AdminHome", admins.AdminHome, name="AdminHome"),
    path("ViewRegisteredUsers", admins.ViewRegisteredUsers, name="ViewRegisteredUsers"),
    path("AdminActivaUsers", admins.AdminActivaUsers, name="AdminActivaUsers"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)