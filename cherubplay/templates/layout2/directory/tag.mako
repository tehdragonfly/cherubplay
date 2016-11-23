<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">Requests tagged "${tag["type"].replace("_", " ")}:${tag["name"]}"</%block>
    % if request.has_permission("tag_wrangling"):
    % if can_be_approved:
    <form class="tile2" action="${request.route_path("directory_tag_approve", **request.matchdict)}" method="post">
      <h3>Not approved</h3>
      <p class="middle_actions"><button type="submit">Approve</button></p>
    </form>
    % endif
    % if not synonyms:
    <form class="tile2" action="${request.route_path("directory_tag_make_synonym", **request.matchdict)}" method="post">
      <h3>Make this a synonym</h3>
      <p><select name="tag_type" required>
        <option value=""></option>
        % for tag_type in Tag.type.type.enums:
        <option value="${tag_type}">${tag_type.replace("_", " ")}</option>
        % endfor
      </select><input type="text" name="name" maxlength="100" required><button type="submit">Save</button></p>
    </form>
    % endif
    % if synonyms or parents or children:
    <section class="tile2">
      <h3>Related tags</h3>
      % if synonyms:
      <h4 class="request_tag_label">Tags with the same meaning</h4>
      <ul class="tag_list related">
        % for synonym in synonyms:
        <li>${synonym.type.replace("_", " ")}:${synonym.name}</li>
        % endfor
      </ul>
      % endif
      % if parents:
      <h4 class="request_tag_label">Parents</h4>
      <ul class="request_tags related">
        % for tag in parents:
        <li><a href="${request.route_path("directory_tag", type=tag.type, name=tag.url_name)}">${tag.type.replace("_", " ")}:${tag.name}</a></li>
        % endfor
      </ul>
      % endif
      % if children:
      <h4 class="request_tag_label">Children</h4>
      <ul class="request_tags related">
        % for tag in children:
        <li><a href="${request.route_path("directory_tag", type=tag.type, name=tag.url_name)}">${tag.type.replace("_", " ")}:${tag.name}</a></li>
        % endfor
      </ul>
      % endif
    </section>
    % endif
    % endif
    % if blacklisted:
    <p>This tag can't be shown because it's on your <a href="${request.route_path("directory_blacklist")}">blacklist</a>.</p>
    % elif not requests:
    <p>There are no requests with this tag.</p>
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
