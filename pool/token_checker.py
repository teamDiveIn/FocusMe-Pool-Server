from configuration import basic_config as bc
import jwt
from rest_framework import status
from rest_framework.response import Response
from jwt.exceptions import DecodeError


def verify_token(request):
    token = request.META.get('HTTP_AUTHORIZATION', " ").split(' ')[1]
    print(token)
    decoded = -1
    try:
        valid_data = jwt.decode(token, bc.JWT_SECRET_KEY, algorithms="HS256")
        print(valid_data)
        decoded = valid_data['user_idx']
        print(decoded)
        # request.decoded = decoded
        return decoded
    except DecodeError as d:
        print("Decode error", d)
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
