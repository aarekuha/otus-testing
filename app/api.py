#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations
import re
import json
import datetime
import logging
import hashlib
import uuid
from typing import Any, Callable
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

import app.scoring as scoring
from app.store import Store


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

class Field(object):
    __template__: str
    __example__: str = ""
    required: bool
    nullable: bool

    def __init__(self, required: bool = True, nullable: bool = True) -> None:
        self.required = required
        self.nullable = nullable

    def from_value(self, value: Any) -> Any:
        if not value:
            if not self.nullable:
                raise ValueError(f"Not nullable: invalid value {self.__class__.__name__}")

        if hasattr(self, "__type__"):
            if not isinstance(value, self.__type__):  # type: ignore
                raise ValueError(f"Invalid value type for {self.__class__.__name__}: {type(value)}")

        if hasattr(self, "__template__") and self.__template__:
            if not re.match(f"^{self.__template__}$", str(value)):
                example: str = f" (example: {self.__example__})" if self.__example__ else ""
                raise ValueError(f"Validator: invalid value {self.__class__.__name__}: {self.__template__}{example}")

        if hasattr(self, "custom_validator") and isinstance(self.custom_validator, Callable):  # type: ignore
            self.custom_validator(value)  # type: ignore

        return value

    def __bool__(self) -> bool:
        return False


class CharField(Field):
    __type__ = str

    def __add__(self, another: Any) -> str:
        return another

class ArgumentsField(Field, dict):
    pass


class EmailField(CharField):
    __template__ = r"[A-z0-9_\-\.]+@[A-z0-9_\-]+\.[A-z]{2,3}"
    __example__ = "my.mail@mail.ru"


class PhoneField(Field):
    __template__ = r"\+?[78][0-9\-]{10}"
    __example__ = "+79876543221"


class DateField(Field):
    __example__ = "10.02.1990"

    def from_value(self, value: Any) -> datetime.datetime:
        prepared_value: Any = super().from_value(value=value)
        if isinstance(value, str):
            prepared_value = datetime.datetime.strptime(value, "%d.%m.%Y")
        return prepared_value

    def custom_validator(self, value) -> None:
        try:
            datetime.datetime.strptime(value, "%d.%m.%Y")
        except:
            raise ValueError(f"Invalid value {self.__class__.__name__} {value} (example: {self.__example__}")


class BirthDayField(DateField):
    __valid_days_count__ = 365 * 70

    def custom_validator(self, value) -> None:
        super().custom_validator(value)
        valid_age: datetime.timedelta = datetime.timedelta(days=self.__valid_days_count__)
        value_datetime: datetime.datetime = datetime.datetime.strptime(value, "%d.%m.%Y")
        if datetime.datetime.now() - value_datetime > valid_age:
            raise ValueError(f"Invalid value {self.__class__.__name__} age {value} (Age must be less than 70 years)")



class GenderField(Field):
    __template__ = r"[012]"
    __example__ = "1"


class ClientIDsField(Field, list):
    pass


class BaseRequest(object):
    def __init__(self, src_dict: dict) -> None:
        if not isinstance(src_dict, dict):
            return

        current_fields: dict = self.__class__.__dict__
        for key, field in current_fields.items():
            if not isinstance(field, Field):
                continue
            if key not in src_dict:
                if field.required:
                    raise ValueError(f"Missed required field: {key}(field.__class__.__name__)")
                else:
                    self.__dict__[key] = field
                    continue
            self.__dict__[key] = self.__class__.__dict__[key].from_value(src_dict[key])

    def __repr__(self) -> str:
        attrs_list: list[str] = [f"{key}: {value}" for key, value in self.__dict__.items()]
        attrs: str = ", ".join(attrs_list)
        return f"<{self.__class__.__name__}> {attrs}"


class ClientsInterestsRequest(BaseRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(BaseRequest):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(BaseRequest):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request: MethodRequest):
    if request.is_admin:
        digest_data = datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
    else:
        digest_data = request.account + request.login + SALT
    digest = hashlib.sha512(digest_data.encode()).hexdigest()

    return digest == request.token


def get_response_by_method(method: CharField, arguments: ArgumentsField, store) -> Any:
    if method == "online_score":
        online_score: OnlineScoreRequest = OnlineScoreRequest(src_dict=arguments)
        return {"score": scoring.get_score(**online_score.__dict__, store=store)}

    if method == "clients_interests":
        interests: ClientsInterestsRequest = ClientsInterestsRequest(src_dict=arguments)
        return {cid: scoring.get_interests(store=store, cid=cid) for cid in interests.client_ids}

    raise ValueError(f"Invalid method {method}")



def method_handler(request, ctx, store):
    request_body: dict = request.get("body", {})
    method_request: MethodRequest = MethodRequest(src_dict=request_body)
    if not check_auth(method_request):
        return "Invalid authorization", FORBIDDEN

    response = get_response_by_method(method=method_request.method, arguments=method_request.arguments, store=store)
    return response, OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store: Store

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except ValueError as value_error:
                    response = str(value_error)
                    code = INVALID_REQUEST
                except Exception as exception:
                    logging.exception("Unexpected error: %s" % exception)
                    response = str(exception)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-H", "--store-host", action="store", default="localhost")
    op.add_option("-P", "--store-port", action="store", type=int, default=6379)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    MainHTTPHandler.store = Store(host=opts.store_host, port=opts.store_port)
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
