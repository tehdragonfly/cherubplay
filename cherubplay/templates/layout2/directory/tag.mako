<%inherit file="base.mako" />\
<%block name="heading">Requests tagged "${tag.type.replace("_", " ")}:${tag.name.replace("_", " ")}"</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, request_count, current_page)
%>
    % if paginator.page_count!=1:
    <p class="pager tile">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    <ul id="chat_list">
      % for rq in requests:
      <li class="tile2 request">
        ${parent.render_request(rq)}
      </li>
      % endfor
    </ul>
    % if paginator.page_count!=1:
    <p class="pager tile">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
<%block name="scripts"><script>cherubplay.directory_index();</script></%block>
