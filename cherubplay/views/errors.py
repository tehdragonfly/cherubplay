from pyramid.httpexceptions import HTTPForbidden
from pyramid.renderers import render_to_response
from pyramid.view import forbidden_view_config, notfound_view_config


@forbidden_view_config()
def forbidden(request):
    if request.user is not None:
        resp = render_to_response("errors/forbidden.mako", {}, request=request)
    else:
        resp = render_to_response("layout2/home_guest.mako", { "forbidden": True }, request=request)
    resp.status = "403 Forbidden"
    return resp


@notfound_view_config(append_slash=True)
def not_found(request):
    resp = render_to_response("errors/not_found.mako", {}, request=request)
    resp.status = "404 Not Found"
    return resp

