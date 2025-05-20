from django.urls import path
from . import views
from paypal.standard.ipn import views as paypal_views

urlpatterns = [
    path('login/', views.login_view, name='login_page'),
    path('register/', views.register_view, name='register_page'),
    path('logout/', views.logout_view, name='logout_page'),

    path('payments/<int:expense_id>/',views.payment,name='payments'),
    path('paypal/', paypal_views.ipn, name='paypal-ipn'),
    path('payments/success/<int:expense_id>/',views.payment_success,name='payment-success'),
    path('payments/failed/',views.payment_failed,name='payment-failed'),

    path('groups/',views.groupList, name='group_list'),
    path('groups/<int:group_id>/',views.groupDetail, name='group_detail'),
    path('groups/create/',views.groupCreate, name='group_create'),

    path('expenses/', views.expenseList, name='expense_list'),
    path('expenses/<int:expense_id>/', views.expenseDetail, name='expense_detail'),
    path('get-group-members/<int:group_id>/', views.get_group_members, name='get_group_members'),
    path('expenses/create/', views.expenseCreate, name='expense_create'),

    path('settlement/<int:participant_id>/', views.settlementPayment, name='settlement'),
    path('settlement-success/<int:participant_id>/', views.settlementSuccess, name='settlement-success'),
    path('settlement-failed/', views.settlementFailed, name='settlement-failed'),

    path('user_payments/', views.user_payments_view, name='user_payments'),

    path('profile/', views.profileView, name='profile_view'),
    path('profile/create/', views.profileCreate, name='profile_create'),
    path('profile/update/', views.profileUpdate, name='profile_update'),

    path('',views.homeView, name='home_page'),
]
