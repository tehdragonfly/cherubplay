<%inherit file="base.mako" />\
<%block name="heading">Connection with ${request.context.to_username}</%block>
    <form action="${request.route_path("account_connection_delete", username=request.context.to_username)}" method="post">
      Are you sure you want to delete this connection?
      <div class="actions">
        <div class="left"><a href="${request.route_path("account_connections")}">No</a></div>
        <div class="right"><button type="submit">Yes</button></div>
      </div>
    </form>
    </section>