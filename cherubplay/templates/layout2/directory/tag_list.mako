<%inherit file="base.mako" />\
<%block name="heading">${"Unapproved tags" if request.matched_route.name == "directory_tag_list_unapproved" else "All tags"}</%block>
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
          <a href="${request.route_path("directory_tag", type=tag.type, name=tag.name)}">${tag.type.replace("_", " ")}:${tag.name}</a>
        </li>
        % endfor
      </ul>
    </section>
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
