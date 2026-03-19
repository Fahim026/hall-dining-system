from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, MonthlyDeposit, MealRate, DailyMealEntry,
    MealOffRequest, MealOffLimit, GuestMealRequest,
    BazarEntry, Notification
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'name', 'role', 'phone', 'room_number', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'name']
    ordering = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'phone', 'room_number', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'role', 'phone', 'room_number', 'password1', 'password2'),
        }),
    )


@admin.register(MonthlyDeposit)
class MonthlyDepositAdmin(admin.ModelAdmin):
    list_display = ['student', 'month', 'year', 'deposited_amount', 'is_confirmed']
    list_filter = ['is_confirmed', 'month', 'year']
    search_fields = ['student__name', 'student__email']


@admin.register(MealRate)
class MealRateAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'rate_per_meal', 'total_bazar_cost', 'total_meals_eaten', 'is_finalized']


@admin.register(DailyMealEntry)
class DailyMealEntryAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'breakfast', 'lunch', 'dinner', 'total_meals']
    list_filter = ['date', 'breakfast', 'lunch', 'dinner']
    search_fields = ['student__name']


@admin.register(MealOffRequest)
class MealOffRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'start_date', 'end_date', 'status', 'month', 'year']
    list_filter = ['status', 'month', 'year']
    search_fields = ['student__name']


@admin.register(GuestMealRequest)
class GuestMealRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'guest_name', 'guest_count', 'date', 'meal_type', 'status']
    list_filter = ['status', 'meal_type']


@admin.register(BazarEntry)
class BazarEntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'item_name', 'quantity', 'total_cost', 'purchased_by']
    list_filter = ['month', 'year']


@admin.register(MealOffLimit)
class MealOffLimitAdmin(admin.ModelAdmin):
    list_display = ['max_days_per_month', 'updated_by', 'updated_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read']
