from flask import Blueprint
from ..authentication import requires_authentication

main = Blueprint('main', __name__)

main.before_request(requires_authentication)

from app.main.views import search, meta, admin, update
