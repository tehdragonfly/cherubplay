<%inherit file="base.mako" />\
<%block name="heading">
  % if request.matched_route.name == "directory_yours":
    Your requests
  % elif request.matched_route.name == "directory_user":
    Requests by ${request.matchdict["username"]}
  % else:
    Directory
  % endif
</%block>
    % if len(requests) == 0:
      % if request.matched_route.name == "directory_yours":
        <p>You have no requests. <a href="${request.route_path("directory_new")}">Write a new request</a>.</p>
      % elif request.matched_route.name == "directory_user":
        <p>This user has no requests.</p>
      % else:
        <p>There are no requests. <a href="${request.route_path("directory_new")}">Write a new request</a>.</p>
      % endif
    % else:
    % if "before" in request.GET:
    <p class="pager tile2"><a href="${request.current_route_path(_query={})}">First page</a></p>
    % endif
    <ul id="chat_list">
      % for rq in requests:
      <li class="tile2 request ${rq.status}">
        ${parent.render_request(rq, answered=rq.id in requests.answered)}
      </li>
      % endfor
    </ul>
    % if requests.next_page_start:
    <p class="pager tile2"><a href="${request.current_route_path(_query={"before": requests.next_page_start.isoformat()})}">Next page</a></p>
    % endif
    % endif
