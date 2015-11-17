<%inherit file="base.mako" />\
<%block name="heading">Request #${request.context.id}</%block>
    <section class="tile2 request">
      ${parent.render_request(request.context, expanded=True)}
    </section>
