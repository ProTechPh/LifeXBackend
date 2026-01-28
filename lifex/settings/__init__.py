"""
Django settings for lifex project.

This package contains environment-specific settings:
- base.py: Common settings for all environments
- dev.py: Development environment settings
- prod.py: Production environment settings

Usage:
    Set DJANGO_SETTINGS_MODULE environment variable:
    - Development: lifex.settings.dev
    - Production: lifex.settings.prod
"""

import os

# Default to development settings if not specified
environment = os.getenv('DJANGO_ENV', 'dev')

if environment == 'prod':
    from .prod import *
else:
    from .dev import *
