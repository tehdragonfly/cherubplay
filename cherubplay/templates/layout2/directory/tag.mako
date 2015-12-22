<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">Requests tagged "${tag["type"].replace("_", " ")}:${tag["name"].replace("_", " ")}"</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, request_count, current_page)
%>
    % if request.user.status == "admin":
    <form class="tile2" action="${request.route_path("directory_tag_synonym", **request.matchdict)}" method="post">
      <h3>Make synonym</h3>
      <p><select name="tag_type">
        % for tag_type in Tag.type.type.enums:
        <option value="${tag_type}">${tag_type.replace("_", " ")}</option>
        % endfor
      </select><input type="text" name="name" maxlength="100" required><button type="submit">Save</button></p>
    </form>
    % endif
    % if blacklisted:
    <p>This tag can't be shown because it's on your <a href="${request.route_path("directory_blacklist")}">blacklist</a>.</p>
    % elif not requests:
    <p>There are no requests with this tag.</p>
    % else:
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    <ul id="chat_list">
      % for rq in requests:
      <li class="tile2 request ${rq.status}">
        ${parent.render_request(rq)}
      </li>
      % endfor
    </ul>
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    % endif
