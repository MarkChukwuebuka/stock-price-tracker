from django.urls import path

from account.controllers.user_controller import ListCreateUsersApiView, RetrieveUpdateOrDeleteUserApiView

urlpatterns = [
    path('', ListCreateUsersApiView.as_view()),
    path('<int:user_id>', RetrieveUpdateOrDeleteUserApiView.as_view()),
]
