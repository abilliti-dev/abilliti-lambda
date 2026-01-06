import json
import os
import boto3
from botocore.exceptions import ClientError

# -----------------------------
# Environment / Clients
# -----------------------------
AWS_REGION = os.environ.get("AWS_REGION")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")

if not AWS_REGION:
    raise RuntimeError("Missing required environment variable: AWS_REGION")
if not COGNITO_CLIENT_ID:
    raise RuntimeError("Missing required environment variable: COGNITO_CLIENT_ID")

cognito = boto3.client("cognito-idp", region_name=AWS_REGION)

# -----------------------------
# Helper Functions
# -----------------------------


def _response(status_code, body):
    """Standardized API Gateway response with CORS"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # Replace with your frontend domain in prod
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body),
    }


def require_fields(body, *fields):
    """Check for missing fields; returns a response dict if missing, else None"""
    missing = [f for f in fields if not body.get(f)]
    if missing:
        return _response(
            400,
            {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing)}",
            },
        )
    return None


# -----------------------------
# Cognito Auth Functions
# -----------------------------


def sign_in(body):
    resp = require_fields(body, "username", "password")
    if resp:
        return resp

    username = body["username"]
    password = body["password"]

    try:
        result = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            ClientId=COGNITO_CLIENT_ID,
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        ).get("AuthenticationResult", {})

        return _response(
            200,
            {
                "success": True,
                "data": {
                    "idToken": result.get("IdToken"),
                    "accessToken": result.get("AccessToken"),
                    "refreshToken": result.get("RefreshToken"),
                },
            },
        )

    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"Cognito sign_in error: {e}")
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            return _response(
                401, {"success": False, "error": "Invalid username or password"}
            )
        return _response(400, {"success": False, "error": "Authentication failed"})


def sign_up(body):
    resp = require_fields(body, "email", "password", "firstName", "lastName")
    if resp:
        return resp

    email = body["email"]
    password = body["password"]
    first_name = body["firstName"]
    last_name = body["lastName"]

    try:
        result = cognito.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "given_name", "Value": first_name},
                {"Name": "family_name", "Value": last_name},
            ],
        )
        return _response(
            200,
            {
                "success": True,
                "data": {
                    "userConfirmed": result.get("UserConfirmed"),
                    "userSub": result.get("UserSub"),
                },
            },
        )

    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"Cognito sign_up error: {e}")
        if code == "UsernameExistsException":
            return _response(400, {"success": False, "error": "Email already in use"})
        return _response(400, {"success": False, "error": "Sign up failed"})


def confirm_sign_up(body):
    resp = require_fields(body, "username", "confirmationCode")
    if resp:
        return resp

    username = body["username"]
    code = body["confirmationCode"]

    try:
        cognito.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID, Username=username, ConfirmationCode=code
        )
        return _response(
            200, {"success": True, "data": {"message": "User confirmed successfully"}}
        )

    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"Cognito confirm_sign_up error: {e}")
        if code == "UserNotFoundException":
            return _response(404, {"success": False, "error": "User not found"})
        if code == "CodeMismatchException":
            return _response(
                400, {"success": False, "error": "Invalid confirmation code"}
            )
        if code == "NotAuthorizedException":
            return _response(400, {"success": False, "error": "User already confirmed"})
        return _response(400, {"success": False, "error": "Confirmation failed"})


def reset_password(body):
    resp = require_fields(body, "email")
    if resp:
        return resp

    email = body["email"]

    try:
        cognito.forgot_password(ClientId=COGNITO_CLIENT_ID, Username=email)
        return _response(
            200, {"success": True, "data": {"message": "Password reset initiated"}}
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"Cognito reset_password error: {e}")
        if code == "UserNotFoundException":
            return _response(404, {"success": False, "error": "Email not found"})
        if code == "InvalidParameterException":
            return _response(
                400,
                {
                    "success": False,
                    "error": "Cannot reset password for unverified email",
                },
            )
        return _response(400, {"success": False, "error": "Reset password failed"})


def confirm_reset_password(body):
    resp = require_fields(body, "email", "verificationCode", "password")
    if resp:
        return resp

    email = body["email"]
    code = body["verificationCode"]
    new_password = body["password"]

    try:
        cognito.confirm_forgot_password(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            ConfirmationCode=code,
            Password=new_password,
        )
        return _response(
            200, {"success": True, "data": {"message": "Password reset confirmed"}}
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"Cognito confirm_reset_password error: {e}")
        if code == "CodeMismatchException":
            return _response(
                400, {"success": False, "error": "Invalid verification code"}
            )
        if code == "UserNotFoundException":
            return _response(404, {"success": False, "error": "Email not found"})
        return _response(
            400, {"success": False, "error": "Password confirmation failed"}
        )


# -----------------------------
# Route Mapping
# -----------------------------

ROUTES = {
    "/auth/sign-in": sign_in,
    "/auth/sign-up": sign_up,
    "/auth/confirm-sign-up": confirm_sign_up,
    "/auth/reset-password": reset_password,
    "/auth/confirm-reset-password": confirm_reset_password,
}


def handler(event, context):
    """Main Lambda handler"""
    print(f"Incoming event: {event}")

    path = event.get("rawPath", "").rstrip("/").lower()
    body = {}
    if "body" in event and event["body"]:
        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return _response(400, {"success": False, "error": "Invalid JSON body"})

    route_handler = ROUTES.get(path)
    if route_handler:
        try:
            return route_handler(body)
        except Exception as e:
            print(f"Unhandled error in route {path}: {e}")
            return _response(500, {"success": False, "error": "Internal server error"})
    else:
        return _response(404, {"success": False, "error": f"Unknown endpoint: {path}"})
