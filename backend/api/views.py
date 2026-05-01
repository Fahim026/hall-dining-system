from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from datetime import date, timedelta

from .models import (
    MonthlyDeposit, MealRate, DailyMealEntry,
    MealOffRequest, MealOffLimit, GuestMealRequest,
    BazarEntry, Notification, DiningDay
)
from .serializers import (
    RegisterSerializer, UserSerializer, UserAdminSerializer,
    MonthlyDepositSerializer, DepositConfirmSerializer,
    MealRateSerializer, DailyMealEntrySerializer, BulkMealEntrySerializer,
    MealOffRequestSerializer, MealOffReviewSerializer, MealOffLimitSerializer,
    GuestMealRequestSerializer, GuestMealReviewSerializer,
    BazarEntrySerializer, NotificationSerializer,
    StudentDashboardSerializer, AdminDashboardSerializer,
    DiningDaySerializer
)
from .permissions import IsAdmin, IsStudent, IsAdminOrReadOwn

User = get_user_model()


def create_notification(user, title, message):
    Notification.objects.create(user=user, title=title, message=message)


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        if not user:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({'error': 'Account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class LogoutView(views.APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        return Response({'message': 'Logged out successfully.'})


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(views.APIView):
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect.'}, status=400)
        if len(new_password) < 6:
            return Response({'error': 'New password must be at least 6 characters.'}, status=400)
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully.'})


# ─── ADMIN: USERS ─────────────────────────────────────────────────────────────

class AdminUserListView(generics.ListCreateAPIView):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = User.objects.filter(role='student')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))
        return qs

    def perform_create(self, serializer):
        password = self.request.data.get('password', 'changeme123')
        user = serializer.save()
        user.set_password(password)
        user.save()


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()


class ToggleStudentActiveView(views.APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk, role='student')
        user.is_active = not user.is_active
        user.save()
        return Response({'is_active': user.is_active})


# ─── DEPOSITS ─────────────────────────────────────────────────────────────────

class StudentDepositListView(generics.ListCreateAPIView):
    serializer_class = MonthlyDepositSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            qs = MonthlyDeposit.objects.all().select_related('student', 'confirmed_by')
            month = self.request.query_params.get('month')
            year = self.request.query_params.get('year')
            if month:
                qs = qs.filter(month=month)
            if year:
                qs = qs.filter(year=year)
            return qs
        return MonthlyDeposit.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        today = date.today()
        # Check if deposit already exists for this month
        existing = MonthlyDeposit.objects.filter(
            student=self.request.user,
            month=today.month,
            year=today.year
        ).first()
        if existing:
            raise serializers.ValidationError('Deposit for this month already submitted.')
        serializer.save(student=self.request.user, month=today.month, year=today.year)


class DepositDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MonthlyDepositSerializer
    permission_classes = [IsAdminOrReadOwn]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return MonthlyDeposit.objects.all()
        return MonthlyDeposit.objects.filter(student=self.request.user)


class ConfirmDepositView(views.APIView):
    """Admin confirms that payment was received"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        deposit = get_object_or_404(MonthlyDeposit, pk=pk)
        deposit.is_confirmed = True
        deposit.confirmed_by = request.user
        deposit.confirmed_at = timezone.now()
        deposit.save()
        create_notification(
            deposit.student,
            'Deposit Confirmed',
            f'Your deposit of {deposit.deposited_amount} BDT for {deposit.month}/{deposit.year} has been confirmed.'
        )
        return Response({'message': 'Deposit confirmed.', 'deposit': MonthlyDepositSerializer(deposit).data})


# ─── MEAL RATE ────────────────────────────────────────────────────────────────

class MealRateListView(generics.ListCreateAPIView):
    serializer_class = MealRateSerializer
    permission_classes = [IsAuthenticated]
    queryset = MealRate.objects.all().order_by('-year', '-month')


class MealRateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MealRateSerializer
    permission_classes = [IsAdmin]
    queryset = MealRate.objects.all()


class FinalizeMealRateView(views.APIView):
    """Admin finalizes rate — auto-calculates from bazar cost / meals"""
    permission_classes = [IsAdmin]

    def post(self, request, month, year):
        rate_obj, created = MealRate.objects.get_or_create(month=month, year=year)

        # Calculate total bazar cost
        total_cost = BazarEntry.objects.filter(month=month, year=year).aggregate(
            total=Sum('total_cost'))['total'] or 0

        # Calculate total meals
        total_meals = DailyMealEntry.objects.filter(
            date__month=month, date__year=year
        ).aggregate(total=Sum('total_meals'))['total'] or 0

        rate = round(total_cost / total_meals, 2) if total_meals > 0 else 0

        rate_obj.total_bazar_cost = total_cost
        rate_obj.total_meals_eaten = total_meals
        rate_obj.rate_per_meal = rate
        rate_obj.is_finalized = True
        rate_obj.finalized_by = request.user
        rate_obj.finalized_at = timezone.now()
        rate_obj.save()

        # Notify all students
        students = User.objects.filter(role='student', is_active=True)
        for student in students:
            create_notification(
                student,
                'Meal Rate Updated',
                f'Meal rate for {month}/{year} has been set to {rate} BDT/meal.'
            )

        return Response(MealRateSerializer(rate_obj).data)


# ─── DAILY MEAL ENTRY ────────────────────────────────────────────────────────

class DailyMealEntryListView(generics.ListCreateAPIView):
    serializer_class = DailyMealEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DailyMealEntry.objects.all().select_related('student', 'entered_by')
        if self.request.user.role == 'student':
            qs = qs.filter(student=self.request.user)

        date_param = self.request.query_params.get('date')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        student_id = self.request.query_params.get('student_id')

        if date_param:
            qs = qs.filter(date=date_param)
        if month:
            qs = qs.filter(date__month=month)
        if year:
            qs = qs.filter(date__year=year)
        if student_id and self.request.user.role == 'admin':
            qs = qs.filter(student_id=student_id)

        return qs.order_by('-date')

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)


class DailyMealEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DailyMealEntrySerializer
    permission_classes = [IsAdmin]
    queryset = DailyMealEntry.objects.all()

    def perform_update(self, serializer):
        serializer.save(entered_by=self.request.user)


class BulkMealEntryView(views.APIView):
    """Admin enters meals for all students for a specific date"""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkMealEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry_date = data['date']
        entries = data['entries']
        created, updated = 0, 0

        for entry in entries:
            student_id = entry.get('student_id')
            student = get_object_or_404(User, pk=student_id, role='student')
            obj, is_new = DailyMealEntry.objects.update_or_create(
                student=student,
                date=entry_date,
                defaults={
                    'breakfast': entry.get('breakfast', False),
                    'lunch': entry.get('lunch', False),
                    'dinner': entry.get('dinner', False),
                    'entered_by': request.user,
                }
            )
            if is_new:
                created += 1
            else:
                updated += 1

        return Response({'created': created, 'updated': updated})


# ─── MEAL OFF REQUEST ─────────────────────────────────────────────────────────

class MealOffRequestListView(generics.ListCreateAPIView):
    serializer_class = MealOffRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MealOffRequest.objects.all().select_related('student', 'reviewed_by')
        if self.request.user.role == 'student':
            qs = qs.filter(student=self.request.user)

        status_param = self.request.query_params.get('status')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')

        if status_param:
            qs = qs.filter(status=status_param)
        if month:
            qs = qs.filter(month=month)
        if year:
            qs = qs.filter(year=year)

        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        student = self.request.user
        if student.role != 'student':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only students can request meal off.')

        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        month = start_date.month
        year = start_date.year

        # Get the limit
        limit_obj = MealOffLimit.objects.last()
        max_days = limit_obj.max_days_per_month if limit_obj else 5

        # Count approved days this month
        approved_requests = MealOffRequest.objects.filter(
            student=student,
            month=month,
            year=year,
            status='approved'
        )
        used_days = sum(
            (r.end_date - r.start_date).days + 1
            for r in approved_requests
        )

        new_days = (end_date - start_date).days + 1
        if used_days + new_days > max_days:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f'You have used {used_days}/{max_days} meal-off days this month. '
                f'Cannot request {new_days} more days.'
            )

        serializer.save(student=student, month=month, year=year)


class MealOffRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MealOffRequestSerializer
    permission_classes = [IsAdminOrReadOwn]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return MealOffRequest.objects.all()
        return MealOffRequest.objects.filter(student=self.request.user, status='pending')

    def perform_destroy(self, instance):
        if instance.status != 'pending':
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Cannot cancel a request that is not pending.')
        instance.status = 'cancelled'
        instance.save()


class ReviewMealOffView(views.APIView):
    """Admin approves or rejects meal off request"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        meal_off = get_object_or_404(MealOffRequest, pk=pk)
        serializer = MealOffReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        meal_off.status = data['status']
        meal_off.reviewed_by = request.user
        meal_off.reviewed_at = timezone.now()
        meal_off.admin_note = data.get('admin_note', '')
        meal_off.save()

        status_text = 'approved' if data['status'] == 'approved' else 'rejected'
        create_notification(
            meal_off.student,
            f'Meal Off Request {status_text.title()}',
            f'Your meal off request from {meal_off.start_date} to {meal_off.end_date} has been {status_text}.'
            + (f' Note: {meal_off.admin_note}' if meal_off.admin_note else '')
        )

        return Response(MealOffRequestSerializer(meal_off).data)


class MealOffLimitView(views.APIView):
    """Get or set the monthly meal-off limit"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit_obj = MealOffLimit.objects.last()
        if not limit_obj:
            return Response({'max_days_per_month': 5})
        return Response(MealOffLimitSerializer(limit_obj).data)

    def post(self, request):
        if request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        serializer = MealOffLimitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        limit_obj = serializer.save(updated_by=request.user)
        return Response(MealOffLimitSerializer(limit_obj).data)


# ─── GUEST MEAL ───────────────────────────────────────────────────────────────

class GuestMealRequestListView(generics.ListCreateAPIView):
    serializer_class = GuestMealRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = GuestMealRequest.objects.all().select_related('student', 'reviewed_by')
        if self.request.user.role == 'student':
            qs = qs.filter(student=self.request.user)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        if self.request.user.role != 'student':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only students can request guest meals.')
        serializer.save(student=self.request.user)


class GuestMealDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GuestMealRequestSerializer
    permission_classes = [IsAdminOrReadOwn]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return GuestMealRequest.objects.all()
        return GuestMealRequest.objects.filter(student=self.request.user, status='pending')


class ReviewGuestMealView(views.APIView):
    """Admin approves or rejects guest meal request"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        guest_meal = get_object_or_404(GuestMealRequest, pk=pk)
        serializer = GuestMealReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        guest_meal.status = data['status']
        guest_meal.reviewed_by = request.user
        guest_meal.reviewed_at = timezone.now()
        guest_meal.admin_note = data.get('admin_note', '')
        guest_meal.extra_charge = data.get('extra_charge', 0)
        guest_meal.save()

        status_text = 'approved' if data['status'] == 'approved' else 'rejected'
        create_notification(
            guest_meal.student,
            f'Guest Meal Request {status_text.title()}',
            f'Your guest meal request for {guest_meal.guest_name} on {guest_meal.date} has been {status_text}.'
        )

        return Response(GuestMealRequestSerializer(guest_meal).data)


# ─── BAZAR ────────────────────────────────────────────────────────────────────

class BazarEntryListView(generics.ListCreateAPIView):
    serializer_class = BazarEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = BazarEntry.objects.all().select_related('purchased_by')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        date_param = self.request.query_params.get('date')

        if month:
            qs = qs.filter(month=month)
        if year:
            qs = qs.filter(year=year)
        if date_param:
            qs = qs.filter(date=date_param)

        return qs.order_by('-date', '-created_at')

    def perform_create(self, serializer):
        if self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only admins can add bazar entries.')
        entry_date = serializer.validated_data.get('date', date.today())
        serializer.save(
            purchased_by=self.request.user,
            month=entry_date.month,
            year=entry_date.year
        )


class BazarEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BazarEntrySerializer
    permission_classes = [IsAdmin]
    queryset = BazarEntry.objects.all()

    def perform_update(self, serializer):
        entry_date = serializer.validated_data.get('date', serializer.instance.date)
        serializer.save(month=entry_date.month, year=entry_date.year)


class BazarSummaryView(views.APIView):
    """Monthly bazar cost summary"""
    permission_classes = [IsAuthenticated]

    def get(self, request, month, year):
        entries = BazarEntry.objects.filter(month=month, year=year)
        total = entries.aggregate(total=Sum('total_cost'))['total'] or 0
        return Response({
            'month': month, 'year': year,
            'total_cost': total,
            'entry_count': entries.count(),
            'entries': BazarEntrySerializer(entries.order_by('-date'), many=True).data
        })


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return Response({'message': 'Marked as read.'})

    def delete(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkAllNotificationsReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})


# ─── DASHBOARDS ───────────────────────────────────────────────────────────────

class StudentDashboardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user
        today = date.today()
        month = int(request.query_params.get('month', today.month))
        year = int(request.query_params.get('year', today.year))

        # Deposit
        deposit = MonthlyDeposit.objects.filter(student=student, month=month, year=year).first()
        deposited_amount = deposit.deposited_amount if deposit else 0
        deposit_confirmed = deposit.is_confirmed if deposit else False

        # Meal stats
        meal_entries = DailyMealEntry.objects.filter(
            student=student, date__month=month, date__year=year
        )
        total_meals = meal_entries.aggregate(total=Sum('total_meals'))['total'] or 0

        # Meal rate
        rate_obj = MealRate.objects.filter(month=month, year=year).first()
        meal_rate = rate_obj.rate_per_meal if rate_obj else 0
        total_cost = total_meals * meal_rate

        # Guest meal charges
        guest_charges = GuestMealRequest.objects.filter(
            student=student,
            date__month=month, date__year=year,
            status='approved'
        ).aggregate(total=Sum('extra_charge'))['total'] or 0

        total_cost += guest_charges
        balance = deposited_amount - total_cost

        # Meal off usage
        limit_obj = MealOffLimit.objects.last()
        max_days = limit_obj.max_days_per_month if limit_obj else 5
        approved_offs = MealOffRequest.objects.filter(
            student=student, month=month, year=year, status='approved'
        )
        used_days = sum((r.end_date - r.start_date).days + 1 for r in approved_offs)

        # Pending requests
        pending_meal_offs = MealOffRequest.objects.filter(student=student, status='pending').count()
        pending_guest = GuestMealRequest.objects.filter(student=student, status='pending').count()

        return Response({
            'month': month,
            'year': year,
            'deposited_amount': deposited_amount,
            'deposit_confirmed': deposit_confirmed,
            'total_meals_eaten': total_meals,
            'meal_rate': meal_rate,
            'total_cost': round(total_cost, 2),
            'guest_charges': round(guest_charges, 2),
            'balance_remaining': round(balance, 2),
            'meal_off_days_used': used_days,
            'meal_off_days_limit': max_days,
            'meal_off_days_remaining': max(0, max_days - used_days),
            'pending_requests': {
                'meal_off': pending_meal_offs,
                'guest_meal': pending_guest,
            },
            'unread_notifications': Notification.objects.filter(user=student, is_read=False).count()
        })


class AdminDashboardView(views.APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = date.today()
        month = int(request.query_params.get('month', today.month))
        year = int(request.query_params.get('year', today.year))

        total_students = User.objects.filter(role='student', is_active=True).count()
        total_deposits = MonthlyDeposit.objects.filter(
            month=month, year=year, is_confirmed=True
        ).aggregate(total=Sum('deposited_amount'))['total'] or 0

        total_bazar = BazarEntry.objects.filter(
            month=month, year=year
        ).aggregate(total=Sum('total_cost'))['total'] or 0

        total_meals = DailyMealEntry.objects.filter(
            date__month=month, date__year=year
        ).aggregate(total=Sum('total_meals'))['total'] or 0

        rate_obj = MealRate.objects.filter(month=month, year=year).first()
        meal_rate = rate_obj.rate_per_meal if rate_obj else 0

        pending_meal_offs = MealOffRequest.objects.filter(status='pending').count()
        pending_guest = GuestMealRequest.objects.filter(status='pending').count()
        pending_deposits = MonthlyDeposit.objects.filter(month=month, year=year, is_confirmed=False).count()

        return Response({
            'month': month,
            'year': year,
            'total_students': total_students,
            'total_confirmed_deposits': round(total_deposits, 2),
            'total_bazar_cost': round(total_bazar, 2),
            'total_meals_this_month': total_meals,
            'current_meal_rate': meal_rate,
            'balance': round(total_deposits - total_bazar, 2),
            'pending_meal_offs': pending_meal_offs,
            'pending_guest_meals': pending_guest,
            'pending_deposits': pending_deposits,
        })
    
class DiningDayListView(views.APIView):
    """List and create dining days"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = request.query_params.get('month', timezone.now().month)
        year = request.query_params.get('year', timezone.now().year)
        days = DiningDay.objects.filter(
            date__month=month,
            date__year=year
        )
        serializer = DiningDaySerializer(days, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=403)
        date = request.data.get('date')
        is_open = request.data.get('is_open', True)
        note = request.data.get('note', '')
        # Update or create
        dining_day, created = DiningDay.objects.update_or_create(
            date=date,
            defaults={
                'is_open': is_open,
                'note': note,
                'created_by': request.user
            }
        )
        serializer = DiningDaySerializer(dining_day)
        return Response(serializer.data)


class StudentMealSummaryView(views.APIView):
    """Get student meal summary with dining days and meal off"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month = int(request.query_params.get('month', timezone.now().month))
        year = int(request.query_params.get('year', timezone.now().year))
        student = request.user

        # Get all dining open days this month
        from datetime import date, timedelta
        import calendar

        # Get days in month
        days_in_month = calendar.monthrange(year, month)[1]
        today = date.today()

        # Get closed dining days
        closed_days = set(
            DiningDay.objects.filter(
                date__month=month,
                date__year=year,
                is_open=False
            ).values_list('date', flat=True)
        )

        # Get approved meal off days for this student
        meal_off_requests = MealOffRequest.objects.filter(
            student=student,
            status='approved',
            start_date__year=year,
            start_date__month=month
        )

        meal_off_days = {}
        for req in meal_off_requests:
            current = req.start_date
            while current <= req.end_date:
                if current.month == month:
                    meal_off_days[current] = {
                        'lunch': req.skip_lunch,
                        'dinner': req.skip_dinner
                    }
                current += timedelta(days=1)

        # Build daily summary
        daily_summary = []
        total_lunch = 0
        total_dinner = 0

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            if current_date > today:
                break

            # Check if dining closed
            if current_date in closed_days:
                daily_summary.append({
                    'date': current_date,
                    'lunch': False,
                    'dinner': False,
                    'status': 'dining_closed',
                    'note': 'Dining Closed'
                })
                continue

            # Check meal off
            meal_off = meal_off_days.get(current_date, {})
            lunch = not meal_off.get('lunch', False)
            dinner = not meal_off.get('dinner', False)

            status = 'normal'
            if meal_off:
                status = 'meal_off'

            if lunch:
                total_lunch += 1
            if dinner:
                total_dinner += 1

            daily_summary.append({
                'date': current_date,
                'lunch': lunch,
                'dinner': dinner,
                'status': status,
                'note': 'Meal Off' if meal_off else ''
            })

        # Get meal rate
        try:
            meal_rate_obj = MealRate.objects.get(month=month, year=year)
            meal_rate = float(meal_rate_obj.rate_per_meal)
        except MealRate.DoesNotExist:
            meal_rate = 0

        total_meals = total_lunch + total_dinner
        total_cost = total_meals * meal_rate

        # Get deposit
        try:
            deposit = MonthlyDeposit.objects.get(
                student=student,
                month=month,
                year=year
            )
            deposited = float(deposit.deposited_amount)
        except MonthlyDeposit.DoesNotExist:
            deposited = 0

        balance = deposited - total_cost

        return Response({
            'daily_summary': [
                {
                    'date': str(d['date']),
                    'lunch': d['lunch'],
                    'dinner': d['dinner'],
                    'status': d['status'],
                    'note': d['note']
                } for d in daily_summary
            ],
            'total_lunch': total_lunch,
            'total_dinner': total_dinner,
            'total_meals': total_meals,
            'meal_rate': meal_rate,
            'total_cost': total_cost,
            'deposited_amount': deposited,
            'balance': balance,
            'month': month,
            'year': year
        })
