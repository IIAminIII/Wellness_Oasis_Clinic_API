"""
WSGI config for Wellness_Oasis_Clinic project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Wellness_Oasis_Clinic.settings')

application = get_wsgi_application()

# Django only routes MEDIA_URL while DEBUG is on, and the WhiteNoise middleware
# covers STATIC_ROOT alone, so uploaded files 404 in production. Serve them here
# until Phase 5 moves media to managed object storage. autorefresh is required
# because files uploaded after boot are not in the startup scan.
from django.conf import settings  # noqa: E402  (must follow get_wsgi_application)

if not settings.DEBUG:
    from whitenoise import WhiteNoise  # noqa: E402

    application = WhiteNoise(application, autorefresh=True)
    application.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL)

    # Vercel builds from Git, where media/ is ignored and the filesystem is
    # read-only, so build.sh never runs to copy the demo assets there. Serve
    # them straight from their versioned source folders under the same URLs
    # the ImageField upload_to paths produce.
    for source, prefix in (
        (settings.BASE_DIR / "doctors" / "images", "/media/doctors/images/"),
        (settings.BASE_DIR / "services" / "image", "/media/services/image/"),
    ):
        if source.is_dir():
            application.add_files(str(source), prefix=prefix)

# Vercel's Python runtime discovers the WSGI callable by the name ``app``.
app = application
