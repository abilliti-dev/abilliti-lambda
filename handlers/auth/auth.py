import json
import os
import boto3
from botocore.exceptions import ClientError

# Initialize Cognito client
cognito = boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION"))
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        path = event.get("rawPath", "").lower()

        if path.endswith("/sign-in"):
            return sign_in(body)
        elif path.endswith("/sign-up"):
            return sign_up(body)
        elif path.endswith("/confirm-sign-up"):
            return confirm_sign_up(body)
        elif path.endswith("/reset-password"):
            return reset_password(body)
        elif path.endswith("/confirm-reset-password"):
            return confirm_reset_password(body)
        else:
            return _response(404, {"error": f"Unknown endpoint: {path}"})

    except Exception:
        return _response(500, {"error": "Internal server error"})


# -----------------------------
# Individual Auth Functions
# -----------------------------


def sign_in(body):
    username = body.get("username")
    password = body.get("password")

    if not username or not password:
        return _response(400, {"error": "Username and password are required"})

    try:
        resp = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            ClientId=CLIENT_ID,
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )
        auth = resp.get("AuthenticationResult", {})
        return _response(
            200,
            {
                "idToken": auth.get("IdToken"),
                "accessToken": auth.get("AccessToken"),
                "refreshToken": auth.get("RefreshToken"),
            },
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            return _response(401, {"error": "Invalid username or password"})
        return _response(
            400, {"error": e.response["Error"].get("Message", "Auth error")}
        )


def sign_up(body):
    email = body.get("email")
    password = body.get("password")
    first_name = body.get("firstName")
    last_name = body.get("lastName")

    if not all([email, password, first_name, last_name]):
        return _response(400, {"error": "Missing required fields"})

    try:
        resp = cognito.sign_up(
            ClientId=CLIENT_ID,
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
                "userConfirmed": resp.get("UserConfirmed"),
                "userSub": resp.get("UserSub"),
            },
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            return _response(
                400,
                {
                    "error": "Email already in use",
                    "description": "Use a different email address or log in to existing account",
                },
            )
        return _response(
            400, {"error": e.response["Error"].get("Message", "Sign up error")}
        )


def confirm_sign_up(body):
    username = body.get("username")
    confirmation_code = body.get("confirmationCode")

    if not username or not confirmation_code:
        return _response(400, {"error": "Username and confirmation code are required"})

    try:
        cognito.confirm_sign_up(
            ClientId=CLIENT_ID, Username=username, ConfirmationCode=confirmation_code
        )
        return _response(200, {"message": "User confirmed successfully"})
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UserNotFoundException":
            return _response(404, {"error": "User not found"})
        if code == "CodeMismatchException":
            return _response(400, {"error": "Invalid confirmation code"})
        if code == "NotAuthorizedException":
            return _response(400, {"error": "User already confirmed"})
        return _response(
            400, {"error": e.response["Error"].get("Message", "Confirmation error")}
        )


def reset_password(body):
    email = body.get("email")

    if not email:
        return _response(400, {"error": "Email is required"})

    try:
        cognito.forgot_password(ClientId=CLIENT_ID, Username=email)
        return _response(200, {"message": "Password reset initiated"})
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UserNotFoundException":
            return _response(404, {"error": "Email not found"})
        if code == "InvalidParameterException":
            return _response(
                400,
                {
                    "error": "Cannot reset password for the user as there is no verified email"
                },
            )
        return _response(
            400, {"error": e.response["Error"].get("Message", "Reset password error")}
        )


def confirm_reset_password(body):
    email = body.get("email")
    verification_code = body.get("verificationCode")
    new_password = body.get("password")

    if not all([email, verification_code, new_password]):
        return _response(
            400, {"error": "Email, verification code, and password are required"}
        )

    try:
        cognito.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=verification_code,
            Password=new_password,
        )
        return _response(200, {"message": "Password reset confirmed"})
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "CodeMismatchException":
            return _response(400, {"error": "Invalid verification code"})
        if code == "UserNotFoundException":
            return _response(404, {"error": "Email not found"})
        return _response(
            400,
            {
                "error": e.response["Error"].get(
                    "Message", "Confirm reset password error"
                )
            },
        )


# -----------------------------
# Response Helper
# -----------------------------
def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
