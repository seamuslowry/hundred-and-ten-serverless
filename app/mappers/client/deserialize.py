'''A module to convert client objects to models'''

import base64
from json import loads

import azure.functions as func

from app import models
from app.dtos import client
from app.mappers.constants import UserType
from app.mappers.shared.deserialize import card as __deserialize_card


def user(req: func.HttpRequest) -> models.User:
    '''Create a user object from a passed request'''
    if __parse_user_type(req) == UserType.GOOGLE:
        return __google_user_from_request(req)

    return models.User(__parse_identifier(req), __parse_name(req))


def card(c_card: client.Card) -> models.Card:
    '''Create a card object from a passed client card'''
    return __deserialize_card(c_card)


def __google_user_from_request(req: func.HttpRequest) -> models.GoogleUser:
    '''Create a Google user object from a passed request'''
    return models.GoogleUser(
        f'{UserType.GOOGLE}-{__parse_identifier(req)}',
        __get_claim(req, "name"),
        __get_claim(req, "picture"))


def __parse_user_type(req: func.HttpRequest):
    '''Get the authentication provider for the user'''
    return __get_header(req, "x-ms-client-principal-idp")


def __parse_identifier(req: func.HttpRequest):
    '''Get the unique identifier for the user'''
    return __get_header(req, "x-ms-client-principal-id")


def __parse_name(req: func.HttpRequest):
    '''Get the user's name'''
    return __get_header(req, "x-ms-client-principal-name")


def __get_claims(req: func.HttpRequest):
    '''Get the claims array from the request'''
    token = __get_header(req, "x-ms-client-principal")
    return loads(base64.b64decode(token).decode('utf-8'))['claims'] if token else []


def __get_claim(req: func.HttpRequest, claim: str):
    '''Get a specific claim from the request'''
    claims = __get_claims(req)
    return next((x for x in claims if x['typ'] == claim), {'val': ''})['val']


def __get_header(req: func.HttpRequest, key: str) -> str:
    '''Get a header with the provided key'''
    val = req.headers.get(key)
    if val:
        return val
    raise ValueError(f'Required header {key} not provided')
