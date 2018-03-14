from pyramid.renderers import render_to_response
from pyramid.view import view_config, forbidden_view_config, notfound_view_config


@forbidden_view_config()
def forbidden(request):
    if request.user is not None:
        resp = render_to_response("errors/forbidden.mako", {}, request=request)
        resp.status_int = 403
        return resp
    else:
        return render_to_response("layout2/home_guest.mako", {"forbidden": True}, request=request)


@notfound_view_config(append_slash=True)
def not_found(request):
    resp = render_to_response("errors/not_found.mako", {}, request=request)
    resp.status_int = 404
    return resp


@view_config(context=Exception)
def internal_server_error(request):
    resp = render_to_response("errors/internal_server_error.mako", {}, request=request)
    resp.status_int = 500
    return resp
