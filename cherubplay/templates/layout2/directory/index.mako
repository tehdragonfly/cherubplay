<%inherit file="base.mako" />\
<%block name="heading">${"Your requests" if request.matched_route.name == "directory_yours" else "Directory"}</%block>
    % if not requests:
    <p>${"You have" if request.matched_route.name == "directory_yours" else "There are"} no requests. <a href="${request.route_path("directory_new")}">Write a new request</a>.</p>
    % else:
    % if "before" in request.GET:
    <p class="pager tile2"><a href="${request.current_route_path(_query={})}">First page</a></p>
    % endif
    <ul id="chat_list">
      % for rq in requests:
      <li class="tile2 request ${rq.status}">
        ${parent.render_request(rq)}
      </li>
      % endfor
    </ul>
    % if more:
    <p class="pager tile2"><a href="${request.current_route_path(_query={"before": requests[-1].posted.isoformat()})}">Next page</a></p>
    % endif
    % endif
