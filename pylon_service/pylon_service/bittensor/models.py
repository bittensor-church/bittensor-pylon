# pyright: reportWildcardImportFromLibrary=false
from pylon_commons._unstable.models import *  # noqa: F403

# Contact models intentionally start as pass-through exports of the latest canonical models.
# This module is the seam where contact-only fields may be added later without forcing DTO shape.
