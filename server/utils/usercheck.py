import os
import jwt
from rest_framework.exceptions import AuthenticationFailed
from authentication.models import User
from dotenv import load_dotenv

load_dotenv()

# ------------------------
# Utility for Auth
# ------------------------
def authenticate_request(request, need_user=False):
    token = request.headers.get('Authorization')
    if not need_user:
        return None

    if not token:
        raise AuthenticationFailed('Unauthenticated!')
    try:
        payload = jwt.decode(token, 'secret', algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token expired!')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token!')

    user = User.objects.filter(id=payload['id']).first()
    if not user:
        raise AuthenticationFailed('User not found!')

    # 🔑 Session ID check (important for single device login)
    # if user.session_id != payload.get('session_id'):
    #     raise AuthenticationFailed('Session invalid — logged in from another device!')

    return user