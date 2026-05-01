from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # ── Auth ─────────────────────────────────────────
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', views.MeView.as_view(), name='me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change-password'),

    # ── Admin: User Management ────────────────────────
    path('admin/users/', views.AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:pk>/toggle-active/', views.ToggleStudentActiveView.as_view(), name='toggle-student'),

    # ── Deposits ──────────────────────────────────────
    path('deposits/', views.StudentDepositListView.as_view(), name='deposits'),
    path('deposits/<int:pk>/', views.DepositDetailView.as_view(), name='deposit-detail'),
    path('deposits/<int:pk>/confirm/', views.ConfirmDepositView.as_view(), name='deposit-confirm'),

    # ── Meal Rate ─────────────────────────────────────
    path('meal-rates/', views.MealRateListView.as_view(), name='meal-rates'),
    path('meal-rates/<int:pk>/', views.MealRateDetailView.as_view(), name='meal-rate-detail'),
    path('meal-rates/finalize/<int:month>/<int:year>/', views.FinalizeMealRateView.as_view(), name='finalize-rate'),

    # ── Daily Meal Entry ──────────────────────────────
    path('meal-entries/', views.DailyMealEntryListView.as_view(), name='meal-entries'),
    path('meal-entries/<int:pk>/', views.DailyMealEntryDetailView.as_view(), name='meal-entry-detail'),
    path('meal-entries/bulk/', views.BulkMealEntryView.as_view(), name='bulk-meal-entry'),

    # ── Meal Off Request ──────────────────────────────
    path('meal-off/', views.MealOffRequestListView.as_view(), name='meal-off-list'),
    path('meal-off/<int:pk>/', views.MealOffRequestDetailView.as_view(), name='meal-off-detail'),
    path('meal-off/<int:pk>/review/', views.ReviewMealOffView.as_view(), name='meal-off-review'),
    path('meal-off/limit/', views.MealOffLimitView.as_view(), name='meal-off-limit'),

    # ── Guest Meal ────────────────────────────────────
    path('guest-meals/', views.GuestMealRequestListView.as_view(), name='guest-meals'),
    path('guest-meals/<int:pk>/', views.GuestMealDetailView.as_view(), name='guest-meal-detail'),
    path('guest-meals/<int:pk>/review/', views.ReviewGuestMealView.as_view(), name='guest-meal-review'),

    # ── Bazar ─────────────────────────────────────────
    path('bazar/', views.BazarEntryListView.as_view(), name='bazar'),
    path('bazar/<int:pk>/', views.BazarEntryDetailView.as_view(), name='bazar-detail'),
    path('bazar/summary/<int:month>/<int:year>/', views.BazarSummaryView.as_view(), name='bazar-summary'),

    # ── Notifications ─────────────────────────────────
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/read-all/', views.MarkAllNotificationsReadView.as_view(), name='notifications-read-all'),
    path('notifications/<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='notification-read'),
    path('notifications/<int:pk>/', views.MarkNotificationReadView.as_view(), name='notification-delete'),

    # ── Dashboards ────────────────────────────────────
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student-dashboard'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('dining-days/', views.DiningDayListView.as_view(), name='dining-days'),
    path('meal-summary/', views.StudentMealSummaryView.as_view(), name='meal-summary'),
]
