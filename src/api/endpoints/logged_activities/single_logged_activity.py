from flask_restful import Resource
from flask import g, request

from api.models import Activity, ActivityType
from api.utils.auth import token_required
from api.utils.helpers import response_builder
from .models import LoggedActivity
from .helpers import ParsedResult, parse_log_activity_fields
from .marshmallow_schemas import (
    LogEditActivitySchema, single_logged_activity_schema
)


class LoggedActivityAPI(Resource):
    """Single Logged Activity Resources."""

    decorators = [token_required]

    @classmethod
    def put(cls, logged_activity_id=None):
        """Edit an activity."""
        payload = request.get_json(silent=True)

        if payload:
            log_edit_activity_schema = LogEditActivitySchema()
            log_edit_activity_schema.context = {'edit': True}
            result, errors = log_edit_activity_schema.load(payload)

            if errors:
                return response_builder(dict(validationErrors=errors), 400)

            logged_activity = LoggedActivity.query.filter_by(
                uuid=logged_activity_id,
                user_id=g.current_user.uuid).one_or_none()
            if not logged_activity:
                return response_builder(dict(
                    message='Logged activity does not exist'
                ), 404)
            if logged_activity.status != 'in review':
                return response_builder(dict(
                    message='Not allowed. Activity is already in pre-approval.'
                ), 401)
            if not result.get('activity_type_id'):
                result['activity_type_id'] = logged_activity.activity_type_id

            if not result.get('date'):
                result['date'] = logged_activity.activity_date
            parsed_result = parse_log_activity_fields(
                result, Activity, ActivityType
            )
            if not isinstance(parsed_result, ParsedResult):
                return parsed_result

            # update fields
            logged_activity.name = result.get('name')
            logged_activity.description = result.get('description')
            logged_activity.activity = parsed_result.activity
            logged_activity.photo = result.get('photo')
            logged_activity.value = parsed_result.activity_value
            logged_activity.activity_type = parsed_result.activity_type
            logged_activity.activity_date = parsed_result.activity_date

            logged_activity.save()

            return response_builder(dict(
                data=single_logged_activity_schema.dump(logged_activity).data,
                message='Activity edited successfully'
            ), 200)

        return response_builder(dict(
                                message="Data for creation must be provided."),
                                400)

    @classmethod
    def delete(cls, logged_activity_id=None):
        """Delete a logged activity."""
        logged_activity = LoggedActivity.query.filter_by(
            uuid=logged_activity_id,
            user_id=g.current_user.uuid).one_or_none()

        if not logged_activity:
            return response_builder(dict(
                message='Logged Activity does not exist!'
            ), 404)

        if logged_activity.status != 'in review':
            return response_builder(dict(
                message='You are not allowed to perform this operation'
            ), 403)

        logged_activity.delete()
        return response_builder(dict(), 204)