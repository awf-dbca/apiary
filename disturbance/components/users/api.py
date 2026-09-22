from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import HttpResponse
from django_countries import countries
from ledger_api_client.ledger_models import EmailUserRO as EmailUser
from rest_framework import views, viewsets
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from disturbance.components.users.serializers import (
    MyUserDetailsSerializer,
    UserSerializer,
)

from disturbance.components.organisations.models import (
    Organisation,
)

from disturbance.components.main.utils import (
    get_first_name,
    get_last_name,
)

from disturbance.helpers import is_internal


class GetCountries(views.APIView):
    renderer_classes = [
        JSONRenderer,
    ]

    def get(self, request, format=None):
        country_list = []
        for country in list(countries):
            country_list.append({"name": country.name, "code": country.code})
        return Response(country_list)


class GetProfile(views.APIView):
    renderer_classes = [
        JSONRenderer,
    ]

    def get(self, request, format=None):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class IsNewUser(views.APIView):
    def get(self, request, format=None):
        is_new = "False"
        try:
            is_new = request.session["is_new"]
        except BaseException:
            pass
        return HttpResponse(is_new)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmailUser.objects.none()
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if is_internal(self.request):
            return EmailUser.objects.all()
        elif user.is_authenticated:
            qs = EmailUser.objects.filter(Q(id=user.id))
            return qs
        return EmailUser.objects.none()

    # TODO on_cleanup may require adjustments
    # NOTE: technically should be internal only but effectively is via get_queryset
    @action(
        detail=False,
        methods=[
            "GET",
        ],
    )
    def get_department_users(self, request, *args, **kwargs):
        search_term = request.GET.get("term", "")
        data = (
            self.get_queryset()
            .filter(is_staff=True)
            .filter(
                Q(first_name__icontains=search_term)
                | Q(last_name__icontains=search_term)
            )
            .values("email", "first_name", "last_name")[:10]
        )
        data_transform = [
            {
                "id": person["email"],
                "text": person["first_name"] + " " + person["last_name"],
            }
            for person in data
        ]
        return Response({"results": data_transform})

    @action(
        detail=True,
        methods=[
            "GET",
        ],
    )
    def pending_org_requests(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = OrganisationRequestDTSerializer(
            instance.organisationrequest_set.filter(status="with_assessor"),
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class GetMyUserDetails(views.APIView):
    renderer_classes = [
        JSONRenderer,
    ]

    def get(self, request, format=None):
        serializer = MyUserDetailsSerializer(request.user, context={"request": request})
        return Response(serializer.data)

class GetPersonOrg(views.APIView):

    def get(self, request, format=None):

        if not (is_internal(self.request)):
            return Response()

        search_term = request.GET.get('term', '')
        search_option = request.GET.get('option', 'contains')
        if search_term:
            data_transform = []
            user_data = []
            if search_option == 'contains':            
                user_data = EmailUser.objects.annotate(
                    search_name=Concat('first_name', Value(' '), 'last_name')
                ).filter(
                    Q(search_name__icontains=search_term) |
                    Q(email__icontains=search_term)
                )[:40]

            if search_option == 'starts_with':            
                user_data = EmailUser.objects.annotate(
                    search_name=Concat('first_name', Value(' '), 'last_name')
                ).filter(
                    Q(search_name__istartswith=search_term) |
                    Q(email__istartswith=search_term)
                )[:40]

            if search_option == 'ends_with':            
                user_data = EmailUser.objects.annotate(
                    search_name=Concat('first_name', Value(' '), 'last_name')
                ).filter(
                    Q(search_name__iendswith=search_term) |
                    Q(email__iendswith=search_term)
                )[:40]

            for email_user in user_data:
                text = '{} {}'.format(get_first_name(email_user), get_last_name(email_user))
                email_user_data = {}
                email_user_data['text'] = text
                email_user_data['entity_type'] = 'user'
                email_user_data['id'] = email_user.id
                data_transform.append(email_user_data)

            #Search based on Organisation Requests that been approved
            org_data = Organisation.objects.filter(
                Q(property_cache__name__icontains=search_term) |
                Q(property_cache__abn__icontains=search_term) 
            )[:40]
            for org in org_data:
                text = '{} (ABN: {})'.format(org.name, org.abn)
                data = {}
                data['text'] = text
                data['entity_type'] = 'org'
                data['id'] = org.id
                data_transform.append(data)
            ### order results
            data_transform.sort(key=lambda item: item.get("id"))
            return Response({"results": data_transform})
        return Response()