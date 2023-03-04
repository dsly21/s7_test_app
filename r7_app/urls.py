from django.contrib import admin
from django.urls import path

from users.views import TransferView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('transfer_money/', TransferView.as_view(), name='transfer-money')
]
