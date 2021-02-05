import uuid
import requests
from rest_framework.decorators import api_view
from rest_framework_jwt.authentication import get_authorization_header
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from pool.models import Pool, Member, Interest
from django_redis import get_redis_connection
import jwt
from configuration import basic_config as bc
from datetime import datetime
from pool.token_checker import *

# Redis
pool_token_dao = get_redis_connection("default")
start_time_dao = get_redis_connection("start_time")
breaks_dao = get_redis_connection("break_time")

# Time Format
FMT = '%d:%H:%M:%S'


@api_view(['GET'])
def test(request):
    print("200 please")
    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
def create_interest_for_test(request):
    request.decoded = verify_token(request)
    Interest(interest_name=request.data['interest']).save()
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def pools(request):
    resp = {}
    for i in Pool.objects.all():
        resp['pool_id'] = i['pool_id']
        resp['communication_mode'] = i['communication_mode']
        resp['current_population'] = i['current_population']
        resp['max_population'] = i['max_population']
        resp['interests'] = i['interest'].objects.values_list('interest_name', flat=True)

    return JsonResponse(resp)


@api_view(['POST'])
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

    # interest의 배열들?
    pool_record = Pool(pool_id=pool_id,
                       pool_name=request.data['pool_name'],
                       communication_mode=request.data['communication_mode'],
                       max_population=request.data['max_population'])
    print((request.data['interest']))
    for name in request.data['interest']:
        print(name)
        try:
            # item = Interest.objects.get(interest_idx=5)
            # item.interest_name = "영어말하기"
            # pool_record.interest.add(item)
            pool_record.interest.add(Interest.objects.get(interest_name=name))
        except Exception as e:
            print(e)
            print("exceptttttttttttttttt")
            # pass

    pool_record.save()

    return JsonResponse({"pool_id": pool_id})


@api_view(['POST'])
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
        "socket_token" : "wss://~~",
        "pool_info" :{
                "pool_id" : "",
                "pool_name" : "",
                "interest" : [
                            "sw-hackaton",
                            "focuswithme"
                            ]
                "communication_mode" : "silent",
                "current_population": 2,
                "max_population": 6,
                }
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
    request.decoded = verify_token(request)
    user_idx = request.decoded
    pool_id = request.data['pool_id']

    try:
        headers = {"Authorization": "Bearer " + request.META.get('HTTP_AUTHORIZATION', " ").split(' ')[1]}
        print(headers)
        # 1. socket connection을 WebRTC 서버와 client가 맺을 수 있도록 token 대신 받아 전해줌
        response = requests.post('https://webrtc.clubapply.com/webrtc/token',
                                 data={'session': pool_id, 'userId': user_idx}, headers=headers)

        socket_token = response.json()['token']
        print(socket_token)
        # 2. cache 에 받은 token을 저장
        pool_token_dao.hset(pool_id, user_idx, socket_token)

        # 3. 입장 시간 cache 에 기록
        start_time_dao.set(user_idx, str(datetime.now()))

        # 3. 해당 풀에 대한 정보 update 및 response에 세팅
        pool_record = Pool.objects.get(pool_id=request.data['pool_id'])
        pool_record.current_population += 1
        pool_info = {'pool_id': pool_record.pool_id,
                     'pool_name': pool_record.pool_name,
                     'communication_mode': pool_record.communication_mode,
                     'current_population': pool_record.current_population,
                     'max_population': pool_record.max_population,
                     'interests': list(pool_record.interest.values_list('interest_name', flat=True))}
        print(pool_info['interests'])
        pool_record.save()

        # 4. 풀 내 멤버 정보를 DB or cache에서 가져와서 response에 세팅
        member_info = []
        headers = {"Authorization": "Bearer " + request.META.get('HTTP_AUTHORIZATION', " ").split(' ')[1]}
        response = requests.post('https://api.divein.club/api/auth/user/verify', headers=headers)

        Member(member_idx=user_idx, nickname=response.json()['data']['nickname'], level="gold",
               pool_id_id=pool_id).save()

        member_records = Member.objects.filter(pool_id=pool_record.pool_id)
        print(member_records)

        for k, member_obj in enumerate(member_records):
            member_idx = member_obj.member_idx
            print(member_obj.nickname)
            start_time = start_time_dao.get(member_idx)
            print(start_time)
            break_time = list(map(lambda x: x.decode('UTF-8'), breaks_dao.lrange(member_idx, 0, -1)))
            for i in break_time:
                print(i)
            member_info += [{"nickname": member_obj.nickname, "start_time": start_time, "break_time": break_time}]
            print(member_info)

        # 5. 풀의 메타정보, 멤버 정보를 response body 에 세팅
        resp['socket_token'] = socket_token
        resp['pool_info'] = pool_info
        resp['member_info'] = member_info

        return JsonResponse(resp)

    except Exception as e:
        print(e)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def leave(request):
    """
    :param request:
    :return:
    """
    request.decoded = verify_token(request)
    user_idx = request.decoded
    breaks_dao.rpush(user_idx, str(datetime.now()))
    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
def exit_with_reward(request):
    """
    :param request:
    :return:
    """
    try:
        request.decoded = verify_token(request)
        user_idx = request.decoded
        print("===================================")
        pool_id = Member.objects.get(member_idx=user_idx).pool_id
        print(pool_id)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        token = pool_token_dao.hget(pool_id, user_idx)
        print(token)
        print("this was token")
        headers = {"Authorization": "Bearer " + request.META.get('HTTP_AUTHORIZATION', " ").split(' ')[1]}
        response = requests.delete('https://webrtc.clubapply.com/webrtc/token',
                                   data={'session': pool_id, 'token': token}, headers=headers)
        print(response)
        print(response.status_code)
        if response.status_code == 200:
            # 토큰 삭제
            pool_token_dao.hdel(pool_id, user_idx)
            start_time_dao.expire(user_idx, 0)
            breaks_dao.expire(user_idx, 0)
            print("after expiration")

            pool_record = Pool.objects.get(pool_id=pool_id)
            pool_record.current_population -= 1
            print("pool population change")

            member_record = Member.objects.get(member_idx=user_idx)
            level = member_record.level
            member_record.pool_id = ""  # member의 pool_id 초기화
            member_record.save()
            print(level)
            return JsonResponse({'level': level})
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
