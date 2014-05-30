import uuid

from django.db import models
import ipaddress
import re


def generate_uuid():
    '''Generate a nice unique number (str).'''
    return str(uuid.uuid4())


class Client(models.Model):
    name = models.CharField(max_length=100)
    uuid = models.CharField(max_length=36, default=generate_uuid())

    def ip_valid(self, ip_address):
        return self._valid('ipfilter_set', ip_address)

    def path_valid(self, path):
        return self._valid('pathfilter_set', path)

    def _valid(self, attr, value):
        include_query = getattr(self, attr).filter(include=True)
        # if there are no include filters, the value is not excluded,
        # otherwise the value is allowed if there is at least include filter 
        # for which it is valid
        include = not include_query.exists() or any(
            filt.valid(value)
            for filt in include_query
        )
        # the value is valid if it is explicitly included (see above) and
        # there are no exclusion rules that apply
        return include and all(
            filt.valid(value)
            for filt in getattr(self, attr).filter(include=False)
        )

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.uuid)

    class Meta(object):
        app_label='djanalytics'


class RequestEvent(models.Model):
    ip_address = models.IPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    tracking_key = models.CharField(max_length=36, default=generate_uuid)
    tracking_user_id = models.CharField(max_length=36, default=generate_uuid)
    protocol = models.CharField(max_length=10)
    domain = models.CharField(max_length=100)
    path = models.URLField(blank=True)
    query_string = models.TextField(null=True, blank=True)
    method = models.CharField(max_length=5, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    response_code = models.IntegerField(null=True, blank=True)
    client = models.ForeignKey(Client)

    class Meta(object):
        app_label='djanalytics'


class Domain(models.Model):
    pattern = models.CharField(max_length=100)
    client = models.ForeignKey(Client)

    def __unicode__(self):
        return '%s: %s' % (self.client.name, self.pattern)

    class Meta(object):
        app_label='djanalytics'


class IPFilter(models.Model):
    netmask = models.CharField(max_length=19)
    include = models.BooleanField()
    client = models.ForeignKey(Client)

    def valid(self, ip_address):
        return self.include == (
            ipaddress.ip_address(unicode(ip_address))
            in ipaddress.ip_network(unicode(self.netmask))
        )

    def __unicode__(self):
        return '%s: %s' % (self.client.name, self.netmask)

    class Meta(object):
        app_label='djanalytics'


class PathFilter(models.Model):
    path_pattern = models.CharField(max_length=200)
    include = models.BooleanField()
    client = models.ForeignKey(Client)

    def valid(self, path):
        if re.match(self.path_pattern, path):
            return self.include
        return not self.include

    def __unicode__(self):
        return '%s: %s' % (self.client.name, self.path_pattern)

    class Meta(object):
        app_label='djanalytics'

