from urllib.parse import quote

from django.conf import settings
from storages.backends.s3 import S3Storage
from storages.utils import clean_name


class SupabaseStorage(S3Storage):
    """Supabase Storage kupitia S3 protocol.

    Inapakia faili kwa S3 API, lakini inarudisha link ya umma ya Supabase,
    ambayo WhatsApp inaweza kuifungua kupakua kadi. Bucket lazima iwe "Public".
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        name = self._normalize_name(clean_name(name))
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{self.bucket_name}/{quote(name)}"
