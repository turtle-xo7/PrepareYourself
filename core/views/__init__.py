"""core.views package — split from the original monolithic views.py.

Every view module star-exports its public names so `from core import views`
(used by core/urls.py) keeps working exactly as before.
"""
from .base import *  # noqa: F401,F403
from .auth import *  # noqa: F401,F403
from .payments import *  # noqa: F401,F403
from .pages import *  # noqa: F401,F403
from .dashboard import *  # noqa: F401,F403
from .question_bank import *  # noqa: F401,F403
from .superadmin import *  # noqa: F401,F403
from .manage import *  # noqa: F401,F403
from .teacher import *  # noqa: F401,F403
from .notes import *  # noqa: F401,F403
from .contests import *  # noqa: F401,F403
from .profile import *  # noqa: F401,F403
from .syllabus import *  # noqa: F401,F403
from .exports import *  # noqa: F401,F403
from .exams import *  # noqa: F401,F403
from .gamification import *  # noqa: F401,F403
