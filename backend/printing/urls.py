from django.urls import path
from . import views

urlpatterns = [
    path('card/<uuid:uuid>/', views.preview_card, name='preview_card'),
    path('card/<uuid:uuid>/print/', views.print_card_trigger, name='print_card_trigger'),
]
