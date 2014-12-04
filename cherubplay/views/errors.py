from pyramid.httpexceptions import HTTPForbidden
from pyramid.renderers import render_to_response
from pyramid.view import forbidden_view_config, notfound_view_config


@forbidden_view_config()
def forbidden(request):
    if request.user is not None:
        return render_to_response("errors/forbidden.mako", {}, request=request)
    else:
        return render_to_response("home_guest.mako", { "forbidden": True }, request=request)


@notfound_view_config(append_slash=True)
def not_found(request):
    return render_to_response("errors/not_found.mako", {}, request=request)

