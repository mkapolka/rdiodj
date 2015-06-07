import httplib

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from redis import ConnectionPool, StrictRedis
from ws4redis.publisher import RedisPublisher
from ws4redis.redis_store import RedisMessage

from sutrofm.redis_models import Party, User, Messages


redis_connection_pool = ConnectionPool(**settings.WS4REDIS_CONNECTION)


def get_party_by_id(request, party_id):
  redis = StrictRedis(connection_pool=redis_connection_pool)
  party = Party.get(redis, party_id)

  if party:
    return JsonResponse(convert_party_to_dict(party))
  else:
    return HttpResponseNotFound()


def parties(request):
  redis = StrictRedis(connection_pool=redis_connection_pool)
  parties = Party.getall(redis)
  data = [convert_party_to_dict(party) for party in parties]
  return JsonResponse({'results': data})


def convert_party_to_dict(party):
  return {
    "id": party.id,
    "name": party.name,
    "people": [{'id': user.id, 'displayName': user.display_name} for user in party.users],
    "player": {
      "playingTrack": {
        "trackKey": party.playing_track_id
      }
    }
  }


def users(request):
  redis = StrictRedis(connection_pool=redis_connection_pool)
  users = User.getall(redis)
  data = [
    {
      "id": user.id,
      "displayName": user.displayName,
      "iconUrl": user.iconUrl,
      "userUrl": user.userUrl,
      "rdioKey": user.rdioKey,
    } for user in users
  ]
  return JsonResponse({'results': data})


def get_user_by_id(request, user_id):
  redis = StrictRedis(connection_pool=redis_connection_pool)
  user = User.get(redis, user_id)
  data = {
    "id": user.id,
    "displayName": user.displayName,
    "iconUrl": user.iconUrl,
    "userUrl": user.userUrl,
    "rdioKey": user.rdioKey,
  }
  return JsonResponse(data)


def messages(request, party_id):
  if request.method == "POST":
    post_message(request, party_id)

  redis = StrictRedis(connection_pool=redis_connection_pool)
  messages = Messages.get_recent(redis, party_id)

  return JsonResponse({'results': messages})

def post_message(request, party_id):
  message = request.POST.get('message')
  message_type = request.POST.get('messageType')
  user = request.POST.get('userId')  # TODO this should come from the session

  m = Messages()
  redis = StrictRedis(connection_pool=redis_connection_pool)
  m.save_message(redis, message, message_type, user, party_id)

  redis_publisher = RedisPublisher(facility=party_id, broadcast=True)
  redis_message = RedisMessage(message)  # TODO format correctly. This is the message's text only
  redis_publisher.publish_message(redis_message)

  return HttpResponse(status=httplib.CREATED)
