from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from picture_upload import views as picture_upload_views

router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),  # Include the router's URL patterns for the notes app
    path('picture_upload/', picture_upload_views.upload_picture, name='upload_picture'),
]
