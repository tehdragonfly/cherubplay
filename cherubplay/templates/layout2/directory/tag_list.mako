<%inherit file="base.mako" />\
<%block name="heading">
% if request.matched_route.name == "directory_tag_list_unapproved":
Unapproved tags
% elif request.matched_route.name == "directory_tag_list_blacklist_default":
Blacklist default tags
% else:
All tags
% endif
</%block>
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
          <a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}">${tag.type.ui_value}:${tag.name}</a>
          % if not tag.approved and not tag.synonym_id:
          <form class="remove_form" action="${request.route_path("directory_tag_approve", type=tag.type.value, name=tag.url_name)}" method="post">
            <button type="submit">Approve</button>
          </form>
          % endif
          <p class="notes">\
            % if tag.synonym_id is not None:
            Synonym of <a href="${request.route_path("directory_tag", tag_string=tag.synonym_of.tag_string)}">${tag.synonym_of.type.ui_value}:${tag.synonym_of.name}</a>\
            % elif not tag.approved:
            Unapproved\
            % else:
            Approved\
            % endif
            % if tag.blacklist_default:
            · Blacklist default\
            % endif
          </p>
        </li>
        % endfor
      </ul>
    </section>
    % if paginator.page_count > 1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
