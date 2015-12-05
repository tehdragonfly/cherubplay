<%inherit file="base.mako" />\
<%block name="heading">Delete request #${request.context.id}</%block>
    <p>Are you sure you want to delete this request?</p>
    <section class="tile2 request">
      ${parent.render_request(request.context, expanded=True)}
    </section>
    <form class="actions" action="${request.route_path("directory_request_delete", id=request.context.id)}" method="post">
      <div class="right"><button type="submit">Delete request</button></div>
    </form>
