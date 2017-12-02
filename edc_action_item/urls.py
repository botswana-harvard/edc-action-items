"""edc_action_items URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.views.generic.base import RedirectView
from edc_action_item.admin_site import edc_action_item_admin

app_name = 'edc_action_item'

urlpatterns = [
    path('admin/', edc_action_item_admin.urls),
    path('', RedirectView.as_view(url='admin/edc_action_item/'), name='home_url'),
]
