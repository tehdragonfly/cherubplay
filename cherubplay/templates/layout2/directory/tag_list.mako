<%inherit file="base.mako" />\
<%block name="heading">${"Unapproved tags" if request.matched_route.name == "directory_tag_list_unapproved" else "Blacklist default tags" if request.matched_route.name == "directory_tag_list_blacklist_default" else "All tags"}</%block>
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
          <a href="${request.route_path("directory_tag", type=tag.type, name=tag.url_name)}">${tag.type.replace("_", " ")}:${tag.name}</a>
          % if tag.synonym_id is not None:
          <p class="notes">Synonym of <a href="${request.route_path("directory_tag", type=tag.synonym_of.type, name=tag.synonym_of.url_name)}">${tag.synonym_of.type.replace("_", " ")}:${tag.synonym_of.name}</a></p>
          % elif not tag.approved:
          <form class="remove_form" action="${request.route_path("directory_tag_approve", type=tag.type, name=tag.url_name)}" method="post">
            <button type="submit">Approve</button>
          </form>
          <p class="notes">Unapproved</p>
          % else:
          <p class="notes">Approved</p>
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
