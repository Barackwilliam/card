import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Tengeneza msimamizi kutoka DJANGO_SUPERUSER_USERNAME na DJANGO_SUPERUSER_PASSWORD "
        "kama hayupo. Inafaa kwa hosting isiyo na terminal (mfano Render ya bure)."
    )

    def handle(self, *args, **opts):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD hazijawekwa; naruka.")
            return
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Msimamizi '{username}' tayari yupo.")
            return
        User.objects.create_superuser(username=username, email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), password=password)
        self.stdout.write(self.style.SUCCESS(f"Msimamizi '{username}' ametengenezwa."))
