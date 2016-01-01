<%inherit file="base.mako" />\
<%block name="heading">Tags</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, tag_count, current_page, items_per_page=250)
%>
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    <section class="tile2">
      <ul class="tag_list">
        % for tag in tags:
        <li>
          ${tag.type.replace("_", " ")}:${tag.name}
        </li>
        % endfor
      </ul>
    </section>
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
