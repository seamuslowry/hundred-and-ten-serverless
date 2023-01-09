'''
Endpoint to get users from the DB
'''
import json

import azure.functions as func

from app.decorators import catcher
from app.mappers.client import serialize
from app.services import UserService


@catcher
def main(req: func.HttpRequest) -> func.HttpResponse:
    '''
    Get users
    '''

    return func.HttpResponse(json.dumps(
        list(map(serialize.user, UserService.search(req.params.get('searchText', ''))))))
