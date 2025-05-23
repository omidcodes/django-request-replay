from django.db import models

from django.utils.translation import gettext_lazy as _


class DjangoRequestsHistoryModel(models.Model):
    class RequestMethod(models.TextChoices):
        POST = 'POST', _("POST")
        PUT = 'PUT', _("PUT")
        PATCH = 'PATCH', _("PATCH")
        DELETE = 'DELETE', _("DELETE")

    request_method = models.CharField(_("Request Method"), max_length=6, choices=RequestMethod.choices)
    request_path = models.CharField(_("Request Path"), max_length=1024)
    request_data_text = models.TextField(_("Request Data Text"), blank=True)
    request_data_binary = models.BinaryField(_("Request Data Binary"), blank=True)
    request_content_type = models.TextField(_("Request Content Type"), default='application/json')

    requester_useragent = models.CharField(_("User Agent"), max_length=255, db_index=True)
    requester_ip = models.GenericIPAddressField(_("IP Address"), null=True, db_index=True)
    requester_username = models.CharField(_("Username"), max_length=255, null=True, db_index=True)

    response_code = models.IntegerField(_("Response code"), null=True)
    response_data_text = models.TextField(_("Response data Text"), blank=True)

    created = models.DateTimeField(_("Created"), auto_now_add=True)

    label = models.CharField(_("Label"), max_length=255, null=True)

    # request_data = models.BinaryField(
    #     blank=True,
    # )
