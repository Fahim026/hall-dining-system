from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    MonthlyDeposit, MealRate, DailyMealEntry,
    MealOffRequest, MealOffLimit, GuestMealRequest,
    BazarEntry, Notification
)

User = get_user_model()


# ─── AUTH ────────────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'name', 'phone', 'room_number', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'phone', 'room_number', 'is_active', 'date_joined']
        read_only_fields = ['id', 'role', 'date_joined']


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'phone', 'room_number', 'is_active', 'date_joined']


# ─── DEPOSIT ─────────────────────────────────────────────────────────────────

class MonthlyDepositSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.name', read_only=True)

    class Meta:
        model = MonthlyDeposit
        fields = '__all__'
        read_only_fields = ['student', 'is_confirmed', 'confirmed_by', 'confirmed_at', 'created_at', 'updated_at']


class DepositConfirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyDeposit
        fields = ['is_confirmed', 'notes']


# ─── MEAL RATE ────────────────────────────────────────────────────────────────

class MealRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealRate
        fields = '__all__'
        read_only_fields = ['is_finalized', 'finalized_by', 'finalized_at', 'created_at', 'updated_at']


# ─── DAILY MEAL ENTRY ────────────────────────────────────────────────────────

class DailyMealEntrySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.name', read_only=True)

    class Meta:
        model = DailyMealEntry
        fields = '__all__'
        read_only_fields = ['total_meals', 'entered_by', 'created_at', 'updated_at']


class BulkMealEntrySerializer(serializers.Serializer):
    """Admin can submit meal entries for multiple students at once"""
    date = serializers.DateField()
    entries = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of {student_id, breakfast, lunch, dinner}'
    )


# ─── MEAL OFF REQUEST ────────────────────────────────────────────────────────

class MealOffRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True)
    days_count = serializers.SerializerMethodField()

    class Meta:
        model = MealOffRequest
        fields = '__all__'
        read_only_fields = ['student', 'status', 'reviewed_by', 'reviewed_at', 'month', 'year', 'created_at']

    def get_days_count(self, obj):
        return (obj.end_date - obj.start_date).days + 1

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'End date must be after start date.'})
        if start and end:
            days = (end - start).days + 1
            if days > 30:
                raise serializers.ValidationError('Cannot request more than 30 days at once.')
        if not any([data.get('skip_breakfast'), data.get('skip_lunch'), data.get('skip_dinner')]):
            raise serializers.ValidationError('At least one meal type must be selected.')
        return data


class MealOffReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    admin_note = serializers.CharField(required=False, allow_blank=True)


# ─── MEAL OFF LIMIT ──────────────────────────────────────────────────────────

class MealOffLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealOffLimit
        fields = '__all__'
        read_only_fields = ['updated_by', 'updated_at']


# ─── GUEST MEAL ──────────────────────────────────────────────────────────────

class GuestMealRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True)

    class Meta:
        model = GuestMealRequest
        fields = '__all__'
        read_only_fields = ['student', 'status', 'reviewed_by', 'reviewed_at', 'extra_charge', 'created_at']

    def validate_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Cannot request guest meal for past dates.')
        return value


class GuestMealReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    admin_note = serializers.CharField(required=False, allow_blank=True)
    extra_charge = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=0)


# ─── BAZAR ───────────────────────────────────────────────────────────────────

class BazarEntrySerializer(serializers.ModelSerializer):
    purchased_by_name = serializers.CharField(source='purchased_by.name', read_only=True)

    class Meta:
        model = BazarEntry
        fields = '__all__'
        read_only_fields = ['purchased_by', 'month', 'year', 'created_at', 'updated_at']


# ─── NOTIFICATION ────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

class StudentDashboardSerializer(serializers.Serializer):
    """Summary data for student dashboard"""
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    deposited_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    deposit_confirmed = serializers.BooleanField()
    total_meals_eaten = serializers.IntegerField()
    meal_rate = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance_remaining = serializers.DecimalField(max_digits=10, decimal_places=2)
    meal_off_days_used = serializers.IntegerField()
    meal_off_days_limit = serializers.IntegerField()
    meal_off_days_remaining = serializers.IntegerField()
    pending_requests = serializers.DictField()


class AdminDashboardSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_deposits = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_bazar_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_meals_this_month = serializers.IntegerField()
    current_meal_rate = serializers.DecimalField(max_digits=8, decimal_places=2)
    pending_meal_offs = serializers.IntegerField()
    pending_guest_meals = serializers.IntegerField()
    pending_deposits = serializers.IntegerField()
