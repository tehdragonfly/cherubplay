<%inherit file="base.mako" />\
<%block name="heading">Your requests</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, request_count, current_page)
%>
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
