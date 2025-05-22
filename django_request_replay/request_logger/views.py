from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from rest_framework.decorators import api_view
from rest_framework.response import Response
from request_logger.models import DjangoRequestsHistoryModel
from .conf import settings
from .models import DjangoRequestsHistoryModel
from .serializers import DjangoRequestsHistorySerializer


class DjangoRequestsHistoryViewSet(ReadOnlyModelViewSet):
    """
    A viewset for viewing and editing DjangoRequestsHistoryModel instances.
    You can add `filter=` and `order_by=` for better filtering.
    """
    serializer_class = DjangoRequestsHistorySerializer
    queryset = DjangoRequestsHistoryModel.objects.all()
    filter = None
    order_by = "created"

    def get_queryset(self):
        queryset = self.queryset

        id_gt_query_param = self.request.query_params.get('id__gte', None)

        if id_gt_query_param:
            try:
                id_gt = int(id_gt_query_param)
                queryset = queryset.filter(id__gte=id_gt)
            except ValueError as exp:
                raise ValidationError({'id__gte': 'This parameter must be a valid integer.'}) from exp

        filter_criteria = self.filter or {}

        return queryset.filter(**filter_criteria).order_by(f'-{self.order_by}')



@api_view(["DELETE"])
def delete_request_history(request):
    count, _ = DjangoRequestsHistoryModel.objects.all().delete()
    return Response({"status": "history deleted", "records_removed": count})
