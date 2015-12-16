<%inherit file="base.mako" />\
<%block name="heading">${"Your requests" if request.matched_route.name == "directory_yours" else "Directory"}</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, request_count, current_page)
%>
    % if not requests:
    <p>${"You have" if request.matched_route.name == "directory_yours" else "There are"} no requests. <a href="${request.route_path("directory_new")}">Write a new request</a>.</p>
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
