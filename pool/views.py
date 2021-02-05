import uuid
import requests
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication, get_authorization_header
from django.http import JsonResponse
from pool.models import Pool, Member
from django_redis import get_redis_connection
import jwt
from configuration import basic_config as bc

# Redis
pool_token_dao = get_redis_connection("default")
start_time_dao = get_redis_connection("start_time")
breaks_dao = get_redis_connection("break_time")


@api_view(['GET'])
@permission_classes((IsAuthenticated, ))
@authentication_classes((JSONWebTokenAuthentication,))
def pools(request):
    resp = {}
    for i in Pool.objects.all():
        resp['pool_id'] = i['pool_id']
        resp['communication_mode'] = i['communication_mode']
        resp['current_population'] = i['current_population']
        resp['max_population'] = i['max_population']
        resp['interests'] = i['interest'].objects.values_list('interest_name', flat=True)

    return JsonResponse(resp)


@api_view('POST')
@permission_classes((IsAuthenticated, ))
@authentication_classes((JSONWebTokenAuthentication,))
def register(request):
    """
    :param request:
    header :: token
    body
            {
                "pool_name": "fighting",
                "interest" : [
                            "sw-hackaton",
                            "focuswithme"
                             ],
                "communication_mode" : "silent",
                "max_population": 6
            }
    :return:
            {
            "pool_id" : "dkfjk-fkdjfek-abch-ekrji"
            }
    """

    pool_id = str(uuid.uuid4())
    Pool(pool_id=pool_id,
         pool_name=request.POST['pool_name'],
         interest=request.POST['interest'],
         communication_mode=request.POST['communication_mode'],
         max_population=request.POST['max_population']).save()

    return JsonResponse({"pool_id": pool_id})


@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
@authentication_classes((JSONWebTokenAuthentication,))
def enter(request):
    """
    socket 관련 통신
    :param request:
    header :: token
    body
        {
        "pool_id" : "dkfjk-fkdjfek-abch-ekrji"
        }

    :return:
    {
        "pool_name": "fighting"
        "interest" :
                    [
                        "sw-hackaton",
                        "focuswithme"
                    ],
        "pool_info" :{

        }
        "communication_mode" : "silent",
        "current_population": 2,
        "max_population": 6,
        "socket_token" : "wss://~~",
        "member_info" : [
                    {
                    "nickname" : "예준",
                    "start_time" : "",
                    "rest_time" : [
                                    ]
                    },
                    {
                    "nickname" : "지오",
                    "start_time" : "",
                    "rest_time" : [
                                    ]
                    }
    }
    """
    resp = {}
    decoded = jwt.decode(get_authorization_header(request).decode('utf-8'), bc.SECRET_KEY)
    user_idx = decoded['user_idx']
    pool_id = Pool.objects.get(user_id=user_idx).pool_id

    try:
        # 1. socket connection을 WebRTC 서버와 client가 맺을 수 있도록 token 대신 받아 전해줌
        response = requests.post('https://www.divein.ga/token',
                                 data={'session': pool_id, 'userId': user_idx})
        socket_token = response.json()[0]['token']

        # 2. cache 에 받은 token을 저장
        get_redis_connection("pool").hset(pool_id, user_idx, socket_token)

        resp['socket_token'] = socket_token

        # 3. 해당 풀에 대한 정보 update 및 response에 세팅
        pool_record = Pool.objects.get(pool_id=request.POST['pool_id'])
        pool_record.current_population += 1

        pool_info = {'pool_id': pool_record.pool_id,
                     'pool_name': pool_record.pool_name,
                     'communication_mode': pool_record.communication_mode,
                     'current_population': pool_record.current_population,
                     'max_population': pool_record.max_population,
                     'interests': pool_record.interest.objects.values_list('interest_name', flat=True)}

        pool_record.save()

        # 4. 풀 내 멤버 정보를 DB or cache에서 가져와서 response에 세팅
        member_info = {}
        member_records = Member.objects.filter(pool_id=pool_record.pool_id)

        for member_obj in member_records:
            member_idx = member_obj.member_idx
            start_time = start_time_dao.get(member_idx)
            break_time = breaks_dao.hget(pool_id, member_idx).decode('UTF-8')
            member_info += {"nickname": member_obj.nickname, "start_time": start_time, "break_time": break_time}

        # 5. 풀의 메타정보, 멤버 정보를 response body 에 세팅
        resp['pool_info'] = pool_info
        resp['member_info'] = member_info

        return JsonResponse(resp)

    except:
        return


@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
@authentication_classes((JSONWebTokenAuthentication,))
def leave(request):
    """
    :param request:
    :return:
    TODO socket 써
    """
    decoded = jwt.decode(get_authorization_header(request).decode('utf-8'), bc.SECRET_KEY)
    user_idx = decoded['user_idx']


@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
@authentication_classes((JSONWebTokenAuthentication,))
def back(request):
    """
    TODO 쉬는 시간으로 전환, 서버에 쉬는 시간 기록
    :param request:
    :return:
    """
    return None


@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
@authentication_classes((JSONWebTokenAuthentication,))
def exit_with_reward(request):
    """
    TODO 노드 앞단 서버로 socket connection 끊는 요청 Rest로 보내기, 그 결과 반환
    :param request:
    :return:
    """
    decoded = jwt.decode(get_authorization_header(request).decode('utf-8'), bc.SECRET_KEY)
    user_idx = decoded['user_idx']

    # DB에서 참여하고 있던 pool id 확인
    pool_id = Member.objects.get(member_idx=user_idx).pool_id
    token = pool_token_dao.hget(pool_id, user_idx)
    response = requests.post('https://www.divein.ga', data={'session': pool_id, 'token': token})

    if response.status_code == 200:
        pool_token_dao.hdel(pool_id, user_idx)  # 토큰 삭제
        return JsonResponse({'user_id': user_idx})

