from celery import app
from django.utils import timezone

from crm.models import JitsiCallback
from crm.services.callback_service import CallbackService
from crm.services.user_points_service import UserPointService
from notification.models import APIRequestLogging
from services.log import AppLogger


@app.shared_task
def make_api_request_log(user_id, request_body, view, ref_id, headers, response_status=""):
    AppLogger.print("Request", user_id, request_body, view, ref_id, headers)
    APIRequestLogging.objects.create(
        user_id=user_id if user_id else '', request_body=request_body,
        view=view, ref_id=ref_id, response_status='',
        header=headers
    )


@app.shared_task
def update_api_request_log(ref_id, response_status, response_body="NA"):
    if not isinstance(response_body, str):
        response_body = str(response_body)

    AppLogger.print("Response", ref_id, response_status, response_body)

    d = APIRequestLogging.objects.get(ref_id=ref_id)
    d.response_status = response_status
    d.response_body = response_body
    d.save()


@app.shared_task
def trigger_pull_organization_staffs(organization_id, user_id):
    from crm.services.organization_service import OrganizationService
    from crm.services.staffs_service import StaffService

    organization_service = OrganizationService(None)
    organization, error = organization_service.fetch_single_by_id(organization_id)
    if error:
        AppLogger.print("Unable to fetch staffs for organization", organization_id, error)
        return

    staff_service = StaffService(None)
    staff_service.handle_pull_external_staffs(organization, user_id)


@app.shared_task
def handle_staff_onboarding(ior_id):
    from crm.services.staffs_service import StaffService
    StaffService(None).handle_onboard_many(ior_id)


@app.shared_task
def staff_upload_task_handler(organization_id, user_id, upload_id):
    from crm.services.staffs_service import StaffService
    StaffService(None).handle_onboard_many_from_file(organization_id, user_id, upload_id)


@app.shared_task
def record_user_action_point_task(tracking_id, user_id, action_type, description, time_of_action):
    UserPointService().record_action_point(tracking_id, user_id, action_type, description, time_of_action)


@app.shared_task
def log_jitsi_callback_data(data, created_at=None):
    CallbackService().handle_jitsi_callback(data, created_at)
