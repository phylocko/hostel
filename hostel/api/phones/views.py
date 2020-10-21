from hostel.common.models import Phone, Call
from hostel.clients.models import Client
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed, Http404
from django.views.decorators.csrf import csrf_exempt
import datetime


@csrf_exempt
def bot_message_phone(request, bot_message_id):
    call = get_object_or_404(Call, bot_message_id=bot_message_id)
    phone = call.phone

    if request.method == 'POST':
        """   Data should be:
        {
            'number': 'string',
            'client_id': int,
            'description': 'string',
            'blacklisted': bool,
            'spam': bool
        }
        """
        client_id = request.POST.get('client_id')
        if client_id:
            try:
                client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                return JsonResponse({'error': 'Client doesn\'t exists'}, status=404)
            else:
                phone.client = client

        phone.description = request.POST.get('description', None)
        phone.blacklisted = bool(request.POST.get('blacklisted', False))
        phone.spam = bool(request.POST.get('spam', False))
        phone.save()
        return JsonResponse(phone.as_dict())

    elif request.method == 'GET':
        return JsonResponse(phone.as_dict())

    return HttpResponseNotAllowed(permitted_methods=['POST', 'GET'])


def phone_id(request, phone_id):
    phone = get_object_or_404(Phone, pk=phone_id)

    if request.method == 'GET':
        return JsonResponse(phone.as_dict())

    elif request.method == 'POST':
        """    Data should be:
        {
            'netname': 'megalit',
            'person': 'string',
            'position': 'string',
            'description': 'string',
            'blacklisted': False
        }
        """
        netname = request.POST.get('netname')
        try:
            client = Client.objects.get(netname=netname)
        except Client.DoesNotExist:
            client = None
        phone.client = client
        phone.person = request.POST.get('person')
        phone.position = request.POST.get('position')
        phone.description = request.POST.get('description')
        phone.blacklisted = request.POST.get('blacklisted', False)
        phone.save()
        return JsonResponse(phone.as_dict())
    return HttpResponseNotAllowed(permitted_methods=['GET', 'POST'])


def phone_number(request, number):
    phone = get_object_or_404(Phone, number=number)
    return JsonResponse(phone.as_dict())


@csrf_exempt
def register_call(request):
    """    Data should be:
    {
        # required:
        'phone_number': 'string',
        'bot_message_id': 'int',
        'time': '2020-01-01 00:00:00'

        # optional:
        'netname': 'megalit',
        'description': 'string',
        'blacklisted': False,
        'spam': False

    }
    """

    phone_number = request.POST.get('phone_number')
    phone_number = ''.join([x for x in phone_number if x.isdigit() or x == '+'])
    asterisk_count = request.POST.get('asterisk_count', None)

    try:
        phone = Phone.objects.get(number=phone_number)
    except Phone.DoesNotExist:
        phone = Phone.objects.create(number=phone_number)
        # we use asterisk_count only first time for a number
        if asterisk_count:
            phone.count = int(asterisk_count)

    phone.count += 1
    phone.save()

    bot_message_id = request.POST.get('bot_message_id')
    time = request.POST.get('time')
    time = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
    call = Call(phone=phone, time=time, bot_message_id=bot_message_id)
    call.save()
    return JsonResponse(call.phone.as_dict())


@csrf_exempt
def update_call(request):
    """    Data should be:
    {
        # useless:
        'phone_number': 'string',
        'bot_message_id': 'int',
        'time': '2020-01-01 00:00:00'

        # good:
        'netname': 'megalit',
        'description': 'string',
        'blacklisted': False,
        'spam': False

    }
    """

    bot_message_id = request.POST.get('bot_message_id')
    if not bot_message_id:
        return Http404('No bot_message_id given')

    call = get_object_or_404(Call, bot_message_id=bot_message_id)
    phone = call.phone

    netname = request.POST.get('netname')
    description = request.POST.get('description')
    blacklisted = request.POST.get('blacklisted')
    spam = request.POST.get('spam')

    if netname:
        try:
            client = Client.objects.get(netname=netname)
        except Client.DoesNotExist:
            if description:
                description = '%s, %s' % (netname, description)
            else:
                description = '%s' % netname
        else:
            phone.client = client

    phone.description = description
    phone.save()
    return JsonResponse(phone.as_dict())
