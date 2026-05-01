from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import MinValueValidator


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [('admin', 'Admin'), ('student', 'Student')]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True)
    room_number = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        db_table = 'users'


class MonthlyDeposit(models.Model):
    """Student deposits money at start of month"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()
    deposited_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_confirmed = models.BooleanField(default=False)  # Admin confirms receipt
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_deposits')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'monthly_deposits'
        unique_together = ('student', 'month', 'year')

    def __str__(self):
        return f"{self.student.name} - {self.month}/{self.year} - {self.deposited_amount}"


class MealRate(models.Model):
    """Admin sets meal rate per month based on total cost / total meals"""
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    rate_per_meal = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_bazar_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_meals_eaten = models.PositiveIntegerField(default=0)
    is_finalized = models.BooleanField(default=False)
    finalized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meal_rates'
        unique_together = ('month', 'year')

    def __str__(self):
        return f"Rate {self.month}/{self.year}: {self.rate_per_meal}/meal"


class DailyMealEntry(models.Model):
    """Admin records how many meals each student had each day"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_entries')
    date = models.DateField()
    breakfast = models.BooleanField(default=False)
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    total_meals = models.PositiveIntegerField(default=0)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_meals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_meal_entries'
        unique_together = ('student', 'date')

    def save(self, *args, **kwargs):
        self.total_meals = sum([self.breakfast, self.lunch, self.dinner])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.total_meals} meals"


class MealOffRequest(models.Model):
    """Student requests to skip meals on certain days"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_off_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    skip_breakfast = models.BooleanField(default=False)
    skip_lunch = models.BooleanField(default=False)
    skip_dinner = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_meal_offs')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    month = models.PositiveIntegerField()  # For tracking monthly limit
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meal_off_requests'

    def __str__(self):
        return f"{self.student.name} off {self.start_date} to {self.end_date} [{self.status}]"


class MealOffLimit(models.Model):
    """Admin configures how many meal-off days a student can request per month"""
    max_days_per_month = models.PositiveIntegerField(default=5)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meal_off_limits'

    def __str__(self):
        return f"Max {self.max_days_per_month} days/month"


class GuestMealRequest(models.Model):
    """Student requests a meal for a guest"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guest_meal_requests')
    guest_name = models.CharField(max_length=150)
    guest_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=[
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ])
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_guest_meals')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    extra_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)  # Additional charge for guest meals
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guest_meal_requests'

    def __str__(self):
        return f"{self.student.name} guest meal on {self.date} [{self.status}]"


class BazarEntry(models.Model):
    """Admin records daily bazar/market expenses"""
    date = models.DateField()
    item_name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=50, blank=True)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bazar_entries')
    notes = models.TextField(blank=True)
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bazar_entries'

    def __str__(self):
        return f"{self.date} - {self.item_name} - {self.total_cost}"


class Notification(models.Model):
    """System notifications for students"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.name}: {self.title}"


class DiningDay(models.Model):
    date = models.DateField(unique=True)
    is_open = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        status = 'Open' if self.is_open else 'Closed'
        return f"{self.date} - {status}"
