'''
Endpoint to update yourself in the DB
'''
import json

import azure.functions as func

from utils.decorators import catcher
from utils.mappers.client import deserialize, serialize
from utils.parsers import parse_request
from utils.services import UserService

bp = func.Blueprint()


@bp.function_name("self")
@bp.route(route="self", methods=["PUT", "POST"])
@catcher
def update_self(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Create or update the user
    '''

    overwrite = req.method.upper() == 'PUT'

    identifier, *_ = parse_request(req)

    existing_user = UserService.by_identifier(identifier)
    provided_user = deserialize.user(req, req.get_json())

    save_user = provided_user if overwrite or not existing_user else existing_user

    return func.HttpResponse(json.dumps(
        serialize.user(UserService.save(save_user))))
