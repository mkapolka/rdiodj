import httplib
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest, HttpResponseForbidden
from django.http import JsonResponse
from redis import ConnectionPool, StrictRedis

from sutrofm.redis_models import Party, User, Messages, ChatMessage, FavoriteMessage


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
  if not request.user.is_authenticated():
    return HttpResponseForbidden()

  redis = StrictRedis(connection_pool=redis_connection_pool)
  if not Party.get(redis, party_id):
    return HttpResponseNotFound()

  message_type = request.POST.get('messageType')

  user = request.user.id
  if message_type == 'chat':
    body = request.POST.get('message')
    message = ChatMessage(user, body, datetime.utcnow())
  elif message_type == 'favorite':
    track_id = request.POST.get('trackId')
    message = FavoriteMessage(user, track_id, datetime.utcnow())
  else:
    return HttpResponseBadRequest()

  Messages.save_message(redis, message, party_id)
  Messages.broadcast(party_id, message)

  return HttpResponse(status=httplib.CREATED)
