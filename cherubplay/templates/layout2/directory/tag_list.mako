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
          % if tag.synonym_id is None and not tag.approved:
          <form class="remove_form" action="${request.route_path("directory_tag_approve", type=tag.type, name=tag.name)}" method="post">
            <button type="submit">Approve</button>
          </form>
          % endif
        </li>
        % endfor
      </ul>
    </section>
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
