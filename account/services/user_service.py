import calendar
import datetime

from django.contrib.auth.hashers import make_password
from django.db import models
from django.db.models import Q, QuerySet, Count, F, Case, When, Value, Avg, OuterRef, Subquery
from django.utils import timezone

from account.serializers.user_serializer import UserListSerializer
from services.util import CustomAPIRequestUtil, generate_password, compare_password


class UserService(CustomAPIRequestUtil):
    serializer_class = UserListSerializer

    def __gen_cache_key(self, key_type, user=None, user_id=None):
        if user:
            if key_type == "permission_names":
                return self.generate_cache_key("user", user.id, "perms", "names")
            if key_type == "role_names":
                return self.generate_cache_key("user", user.id, "roles", "names")
        if user_id:
            if key_type == "user_id":
                return self.generate_cache_key("user_id", user_id)
            if key_type == "user_email":
                return self.generate_cache_key("user_email", user_id)
            if key_type == "user_username":
                return self.generate_cache_key("user_username", user_id)

        return ""

    def get_user_permission_names(self, user):
        def __do_get_permission_names():
            if user.is_superuser or user.roles.filter(name__exact=RoleEnum.sysadmin).exists():
                permissions = Permission.objects.values_list("name", flat=True)
            else:
                permissions = Permission.objects.order_by("name").filter(
                    # todo: filter by required user permissions
                    role__permissions__id__in=user.roles.values_list("pk", flat=True)
                ).distinct("name").values_list("name", flat=True)
            return list(permissions), None

        perms, error = self.get_cache_value_or_default(
            self.__gen_cache_key("permission_names", user=user),
            __do_get_permission_names
        )
        if error:
            return []
        return perms

    def fetch_single_profile(self):
        if self.auth_user.user_type == UserTypes.organization_staff:
            staff = Staff.objects.filter(user=self.auth_user).first()
            return {
                'email': self.auth_user.email,
                'username': self.auth_user.username,
                'first_name': self.auth_user.first_name,
                'last_name': self.auth_user.last_name,
                'other_names': self.auth_user.other_names,
                'user_type': self.auth_user.user_type,
                'user_id': self.auth_user.id,
                'image': self.auth_user.image_url,
                'organization': staff.organization.name if staff and staff.organization else None,
                'department_name': staff.department.name if staff and staff.department else None,
                'department_id': staff.department.id if staff and staff.department else None,
                'career_path_name': staff.career_path.name if staff and staff.career_path else None,
                'career_path_id': staff.career_path.id if staff and staff.career_path else None,
                'phone_number': self.auth_user.phone_number,
                'staff_id': staff.staff_id if staff else None,
                'location': staff.location if staff else None,
                "otp_enabled": self.auth_user.otp_enabled,
                "2fa_type": self.auth_user.auth_2fa_type,
            }
        elif self.auth_user.user_type == UserTypes.organization_admin:
            return {
                'first_name': self.auth_user.first_name,
                'last_name': self.auth_user.last_name,
                'other_names': self.auth_user.other_names,
                'email': self.auth_user.email,
                'user_type': self.auth_user.user_type,
                'username': self.auth_user.username,
                'phone_number': self.auth_user.phone_number,
                'roles': list(self.auth_user.roles.values_list("name", flat=True)),
                "otp_enabled": self.auth_user.otp_enabled,
                "2fa_type": self.auth_user.auth_2fa_type,
                'organization_name': self.auth_organization.name if self.auth_organization else None,
                'organization_id': self.auth_organization.id if self.auth_organization else None,
            }
        else:
            return {
                'first_name': self.auth_user.first_name,
                'last_name': self.auth_user.last_name,
                'other_names': self.auth_user.other_names,
                'username': self.auth_user.username,
                'email': self.auth_user.email,
                'user_type': self.auth_user.user_type,
                'phone_number': self.auth_user.phone_number,
                "otp_enabled": self.auth_user.otp_enabled,
                "2fa_type": self.auth_user.auth_2fa_type,
            }

    def fetch_single_profile_badges(self, username=None, user=None):
        if not user:
            if username is not None:
                user, error = self.fetch_single_by_username(username)
                if error:
                    return None, error
            else:
                user = self.auth_user

        return UserBadge.available_objects.filter(
            status__in=[UserBadgeStatuses.inactive, UserBadgeStatuses.active],
            user=user
        ).annotate(
            badge_url=F("badge__upload__file_url"),
            badge_name=F("badge__name"),
            badge_description=F("badge__description")
        ), None

    def fetch_dashboard_data(self):
        if self.is_staff:
            course_counts = CourseEnrollment.objects.filter(user=self.auth_user).aggregate(
                enrolled_count=Count('id', filter=Q(completed_at__isnull=True)),
                completed_count=Count('id', filter=Q(completed_at__isnull=False))
            )

            last_graded_assessment = AssessmentAttempt.objects.filter(
                user=self.auth_user,
                attempt_status=AssessmentAttemptStatuses.graded
            ).order_by('-graded_at').first()

            attempt_counts = AssessmentAttempt.objects.filter(
                user=self.auth_user, attempt_status=AssessmentAttemptStatuses.graded
            ).aggregate(
                assessment_count=Count('id', filter=Q(assessment_type=AssessmentTypes.assessment)),
                professional_exam_count=Count('id', filter=Q(assessment_type=AssessmentTypes.professional_exam))
            )

            return {
                'enrolled_courses_count': course_counts.get("enrolled_count") or 0,
                'completed_courses_count': course_counts.get("completed_count") or 0,
                'last_assessment_score': last_graded_assessment.score if last_graded_assessment else None,
                'assessment_count': attempt_counts.get("assessment_count") or 0,
                'professional_exam_count': attempt_counts.get("professional_exam_count") or 0
            }
        elif self.is_organization_admin:
            today = timezone.now()
            current_month = today.month
            current_year = today.year
            previous_month = current_month - 1 if current_month > 1 else 12
            current_week = today.isocalendar()[1]
            current_day = today.weekday()  # Monday = 0 ... Sunday = 6

            # Calculate date ranges
            start_of_current_week = today - datetime.timedelta(days=current_day)
            start_of_last_week = start_of_current_week - datetime.timedelta(weeks=1)
            start_of_current_month = timezone.datetime(year=current_year, month=current_month, day=1)
            start_of_last_month = timezone.datetime(year=current_year, month=previous_month, day=1)
            start_of_current_year = timezone.datetime(year=current_year, month=1, day=1)
            start_of_last_year = timezone.datetime(year=current_year - 1, month=1, day=1)

            total_active_users = User.available_objects.filter(
                organization=self.auth_organization, deactivated_at__isnull=True
            ).exclude(pk=self.auth_user.pk).count()

            # Weekly new signups and percentage change
            total_new_signups_week = User.available_objects.filter(
                organization=self.auth_organization, created_at__gte=start_of_current_week
            ).exclude(pk=self.auth_user.pk).count()

            previous_week_signups = User.available_objects.filter(
                organization=self.auth_organization, created_at__gte=start_of_last_week,
                created_at__lt=start_of_current_week
            ).exclude(pk=self.auth_user.pk).count()

            new_signups_percentage_change_week = (
                (total_new_signups_week - previous_week_signups) / previous_week_signups * 100
                if previous_week_signups else 0
            )

            # Monthly new signups and percentage change
            total_new_signups_month = User.available_objects.filter(
                organization=self.auth_organization, created_at__gte=start_of_current_month
            ).exclude(pk=self.auth_user.pk).count()

            previous_month_signups = User.available_objects.filter(
                organization=self.auth_organization, created_at__gte=start_of_last_month,
                created_at__lt=start_of_current_month
            ).exclude(pk=self.auth_user.pk).count()

            new_signups_percentage_change_month = (
                (total_new_signups_month - previous_month_signups) / previous_month_signups * 100
                if previous_month_signups else 0
            )

            # Yearly new signups and percentage change
            total_new_signups_year = User.available_objects.filter(
                organization=self.auth_organization, created_at__gte=start_of_current_year
            ).exclude(pk=self.auth_user.pk).count()

            previous_year_signups = User.available_objects.filter(
                organization=self.auth_organization, created_at__gte=start_of_last_year,
                created_at__lt=start_of_current_year
            ).exclude(pk=self.auth_user.pk).count()

            new_signups_percentage_change_year = (
                (total_new_signups_year - previous_year_signups) / previous_year_signups * 100
                if previous_year_signups else 0
            )

            # Monthly signups data
            monthly_signups = {}
            for month in range(1, 13):
                month_name = calendar.month_name[month]
                start_date = timezone.datetime(year=current_year, month=month, day=1)
                end_date = timezone.datetime(year=current_year, month=month,
                                             day=calendar.monthrange(current_year, month)[1])

                new_signups = User.available_objects.filter(
                    organization=self.auth_organization,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                ).count()

                monthly_signups[month_name] = new_signups

            # Most enrolled courses
            most_enrolled_courses = {}
            for course in Course.available_objects.order_by('-total_enrollments')[:3]:
                most_enrolled_courses[course.title] = course.total_enrollments

            # Latest signups
            latest_signups = User.available_objects.filter(
                organization=self.auth_organization
            ).order_by('-created_at')[:15].annotate(
                staff_id=F('staff_record__staff_id'),
                department=F('staff_record__department__name')
            ).values(
                'first_name', 'last_name', 'email', 'staff_id', 'department'
            )

            # Recent activities
            recent_activities = Activity.objects.filter(
                user__organization=self.auth_organization
            ).order_by('-created_at')[:5].annotate(
                name=F('user__first_name')
            ).values(
                "name", "note", "activity_type", "created_at"
            )

            # User engagement data
            users = User.available_objects.filter(organization=self.auth_organization).exclude(pk=self.auth_user.pk)

            user_engagement_data = users.annotate(
                total_questions=Count(
                    'user_assessment_attempt__assessment__question_bank',
                    filter=Q(user_assessment_attempt__assessment__question_bank__isnull=False)
                ),
                attempted_questions=Count('user_assessment_attempt__id')
            ).values('id', 'total_questions', 'attempted_questions')

            total_questions = sum(user['total_questions'] for user in user_engagement_data)
            attempted_questions = sum(user['attempted_questions'] for user in user_engagement_data)
            average_assessment_engagement = (attempted_questions / total_questions) * 100 if total_questions > 0 else 0

            # Average course rating
            average_course_rating = CourseEnrollment.available_objects.filter(
                organization=self.auth_organization, rating__isnull=False
            ).aggregate(Avg('rating'))['rating__avg']

            average_course_completion_rate = CourseEnrollment.available_objects.filter(
                organization=self.auth_organization
            ).aggregate(Avg('completion_percentage'))['completion_percentage__avg']

            users_in_organization = User.available_objects.filter(
                organization=self.auth_organization
            )

            # Subquery to get the latest attempt for each user-assessment pair within the organization
            latest_attempts_subquery = AssessmentAttempt.available_objects.filter(
                user=OuterRef('user'),
                assessment=OuterRef('assessment'),
                user__organization=self.auth_organization
            ).order_by('-graded_at').values('score')[:1]

            # Annotate each assessment attempt with the score of the latest attempt, filtered by organization
            latest_attempts = AssessmentAttempt.available_objects.filter(
                user__in=users_in_organization
            ).annotate(
                latest_score=Subquery(latest_attempts_subquery)
            ).filter(latest_score__isnull=False)

            # Calculate the average score of all latest attempts within the organization
            average_latest_score = latest_attempts.aggregate(Avg('latest_score'))['latest_score__avg']

            return {
                'total_active_users': total_active_users,
                'total_new_signups': total_new_signups_month,
                'new_signups_percentage_change_week': new_signups_percentage_change_week,
                'new_signups_percentage_change_month': new_signups_percentage_change_month,
                'new_signups_percentage_change_year': new_signups_percentage_change_year,
                'average_course_completion_rate': average_course_completion_rate,
                'user_growth': monthly_signups,
                'most_enrolled_courses': most_enrolled_courses,
                'latest_signups': latest_signups,
                'recent_activities': recent_activities,
                'average_assessment_engagement': average_assessment_engagement,
                'average_course_rating': average_course_rating,
                'average_latest_assessment_score': average_latest_score,
            }

        else:
            return dict()

    def get_user_role_names(self, user):
        def __do_get_role_names():
            roles = user.roles.values_list("name", flat=True)
            return list(roles), None

        perms, error = self.get_cache_value_or_default(
            self.__gen_cache_key("role_names", user=user),
            __do_get_role_names
        )
        if error:
            return []
        return perms

    def is_super_user(self, user):
        return user.is_superuser

    def delete(self, username=None, user=None):
        if not user:
            user, error = self.fetch_single_by_username(username)
            if error:
                return None, error

        if user.id == self.auth_user.id:
            return None, self.make_error("Invalid operation.")

        user.deleted_at = timezone.now()
        user.deleted_by = self.auth_user
        user.save()

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.delete, user)

        return user, None

    def hard_delete(self, user):
        """
        Call function at own risk, delete will actually delete without any check.
        Therefore, use with caution!
        """
        user.delete()

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.delete, user)

        return user, None

    def create_single(self, payload):
        from account.tasks import send_default_password_queue

        user_type = payload.get("user_type")

        if not user_type:
            user_type = UserTypes.idss_user

        username = payload.get("username")
        email = payload.get("email")
        phone_number = payload.get("phone_number", "")

        existing = self.user_exists_by_username_or_email(email=email, username=username, phone_number=phone_number)
        if existing:
            return None, self.make_error("User with provided username, email or phone number already exists")

        if phone_number:
            phone_number_exists, error = self.find_user_by_phone_number(phone_number)
            if phone_number_exists:
                return None, self.make_error("Phone number already exists.")

        password = payload.get("password")
        send_password_email = False
        generated_password = None

        if not password:
            generated_password = generate_password()
            password = make_password(generated_password)
            send_password_email = True

        organization = payload.get("organization")

        if self.auth_user and self.auth_user.user_type != UserTypes.idss_user:
            organization = self.auth_organization

            if organization is None:
                return None, self.make_error("Organization cannot be determined")

            if user_type != UserTypes.organization_staff:
                user_type = UserTypes.organization_admin

        user, is_created = User.objects.get_or_create(
            username=username,
            email=email,
            defaults={
                'password': password,
                'user_type': user_type,
                'first_name': payload.get("first_name", ""),
                'last_name': payload.get("last_name", ""),
                'other_names': payload.get("other_names", ""),
                'phone_number': phone_number,
                'organization': organization,
                "created_by": self.auth_user
            }
        )

        if not is_created:
            return None, self.make_error("User already exists")

        if user_type == UserTypes.idss_user:
            role_ids = payload.get("role_ids", [])
            role_names = payload.get("role_names", [])

            if role_names and not isinstance(role_names, list):
                role_names = [role_names]

            roles = []
            role_service = RoleService(self.request)
            if role_ids:
                roles = role_service.fetch_by_ids(role_ids)

            if role_names:
                roles = role_service.fetch_by_names(role_names)

            if roles:
                user.roles.add(*roles)

        user.save()
        user, error = self.fetch_single_by_username(user.username)

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.create, user)

        if send_password_email and generated_password:
            # Send generated password to user's email
            _ = send_default_password_queue.delay(email, generated_password)

        return user, error

    def update_single(self, payload, username=None, user=None):
        if not user:
            user, error = self.fetch_single_by_username(username)

            if user is None:
                return None, "User does not exist"

            if error:
                return None, error

        email = payload.get("email")
        phone_number = payload.get("phone_number")

        if email:
            user_with_email, error = self.find_user_by_email(email)
            if user_with_email and user_with_email != user:
                return None, "Email already exists!"

        if phone_number:
            user_with_phone, error = self.find_user_by_phone_number(phone_number)
            if user_with_phone and user_with_phone != user:
                return None, "Phone number already exists!"

        user.first_name = payload.get("first_name") or user.first_name
        user.last_name = payload.get("last_name") or user.last_name
        user.other_names = payload.get("other_names") or user.other_names
        user.image_url = payload.get("image_url") or user.image_url
        user.email = email or user.email
        user.phone_number = phone_number or user.phone_number

        role_service = RoleService(self.request)

        roles = []

        if payload.get("role_ids"):
            roles = role_service.fetch_by_ids(payload.get("role_ids", []))

        user.roles.clear()
        user.roles.add(*roles)

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.update, user)
        user.save()

        user, error = self.fetch_single_by_username(user.username)

        return user, error

    def fetch_single_by_username(self, username):
        def __fetch():
            user = User.objects.prefetch_related("roles").filter(
                username__iexact=username).first()

            if not user:
                return None, self.make_404(f"User '{username}' not found")
            return user, None

        cache_key = self.__gen_cache_key("user_username", user_id=username.lower())
        user, error = self.get_cache_value_or_default(cache_key, __fetch)
        organization = self.auth_organization
        if user and not self.is_platform_admin and organization and user.organization_id != organization.id:
            return None, self.make_404(f"User '{username}' not found")

        return user, error

    def find_user_by_email(self, email):
        def __fetch():
            user = User.objects.prefetch_related("roles").filter(email__iexact=email).first()
            if not user:
                return None, self.make_404(f"User with email '{email}' not found")
            return user, None

        cache_key = self.__gen_cache_key("user_email", user_id=email.lower())
        return self.get_cache_value_or_default(cache_key, __fetch)

    def change_password(self, payload):
        user = self.auth_user

        if not compare_password(payload.get("password"), user.password):
            return None, self.make_error("Access denied, invalid password.")

        user.set_password(payload.get("new_password"))
        user.save()

        return "Password changed successfully."

    def find_user_by_phone_number(self, phone_number):
        user = User.objects.filter(phone_number__iexact=phone_number).first()
        if not user:
            return None, self.make_404(f"User with phone_number '{phone_number}' not found")
        return user, None

    def user_exists_by_username_or_email(self, email=None, username=None, phone_number=None):
        if not email and not username:
            return False

        q = Q()

        if username:
            q |= Q(username__iexact=username)
        if email:
            q |= Q(email__iexact=email)
        if phone_number:
            q |= Q(phone_number__iexact=phone_number)

        return User.objects.filter(q).exists()

    def activate_or_deactivate(self, payload, username=None, user=None):
        error = None
        if not user:
            user, error = self.fetch_single_by_username(username)
            if error:
                return None, error

        is_activate = payload.get("is_active")
        reason = payload.get("reason", "")
        message = None

        if is_activate and user.deactivated_at is not None:
            user.deactivated_at = None
            user.deactivated_by = None

            user.save()

            self.report_activity(ActivityType.activate, user)
            self.clear_temp_cache(user)

            message = f"{user.username} account activated successful."

        elif not is_activate and user.deactivated_at is None:
            user.deactivated_at = timezone.now()
            user.deactivated_by = self.auth_user
            user.deactivation_reason = reason

            user.save()

            self.report_activity(ActivityType.deactivate, user)
            self.clear_temp_cache(user)

            message = f"{user.username} account deactivated successful."

        else:
            error = self.make_error(
                f"Invalid operation, user is already {'active' if is_activate else 'deactivated'}"
            )
        return message, error

    def disable_user_2fa(self, payload, username=None, user=None):
        if not user:
            user, error = self.fetch_single_by_username(username)
            if error:
                return None, error

        user.otp_enabled = False
        user.otp_verified = False
        user.otp_base32 = None
        user.otp_auth_url = None
        user.auth_2fa_type = None
        user.otp_secret = None
        user.otp_token = None
        user.save()

        self.clear_temp_cache(user)

        self.report_activity(ActivityType.deactivate, user, description="2FA deactivated")

        return {"message": "Disabled successfully"}, None

    def fetch_single_by_id(self, user_id, fresh_data=False):
        def __fetch():
            user = User.available_objects.prefetch_related("roles").filter(pk=user_id).first()
            if not user:
                return None, self.make_404("User not found")
            return user, None

        return self.get_cache_value_or_default(self.__gen_cache_key("user_id", user_id=user_id), __fetch,
                                               require_fresh_data=fresh_data)

    def fetch_list(self, filter_params) -> QuerySet:
        self.page_size = filter_params.get("page_size", 100)
        filter_user_type = filter_params.get("user_type")
        filter_keyword = filter_params.get("keyword")
        filter_status = filter_params.get("status")

        q = Q()
        if filter_keyword:
            q &= (Q(username__icontains=filter_keyword) | Q(first_name__icontains=filter_keyword) |
                  Q(last_name__icontains=filter_keyword) | Q(other_names__icontains=filter_keyword) |
                  Q(phone_number__icontains=filter_keyword) | Q(email__icontains=filter_keyword))

        if filter_status == "active":
            q &= Q(deactivated_at__isnull=True)
        elif filter_status == "inactive":
            q &= Q(deactivated_at__isnull=False)

        if filter_user_type:
            q &= Q(user_type__iexact=filter_user_type)

        if not self.is_platform_admin:
            q &= Q(organization=self.auth_user.organization)

        return self.__get_base_query().filter(q).exclude(
            pk=self.auth_user.pk
        ).order_by("-created_at")

    @classmethod
    def __get_base_query(cls):
        return User.available_objects.prefetch_related("roles").select_related("organization").annotate(
            status=Case(
                When(deactivated_at__isnull=True, then=Value("active")),
                default=Value("inactive"),
                output_field=models.CharField(max_length=25),
            )
        )

    def clear_temp_cache(self, user):
        self.clear_cache(self.__gen_cache_key("permission_names", user_id=user))
        self.clear_cache(self.__gen_cache_key("role_names", user_id=user))
        self.clear_cache(self.__gen_cache_key("user_id", user_id=user.id))
        self.clear_cache(self.__gen_cache_key("user_username", user_id=user.username.lower()))
        self.clear_cache(self.__gen_cache_key("user_email", user_id=user.email.lower()))
        self.clear_cache(self.generate_cache_key("organization", "user", user.id))
        self.clear_cache(self.generate_cache_key("organization", "staff", user.id))

    @classmethod
    def fetch_by_ids(cls, user_ids, organization=None):
        q = Q(id__in=user_ids)
        if organization:
            q &= Q(organization=organization)
        return User.available_objects.filter(q)

    def find_user_by_token(self, token):
        user = User.available_objects.filter(otp_token=token).first()
        if not user:
            return None, self.make_404("User not found")
        return user, None
