<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">
  % if len(request.context.tags) == 1:
    Requests tagged "${request.context.tags[0].type.replace("_", " ")}:${request.context.tags[0].name}"
  % else:
    Requests with ${len(request.context.tags)} tags
  % endif
</%block>
    % if len(request.context.tags) == 1 and not "before" in request.GET:
      % if request.has_permission("directory.manage_tags"):
        <% current_tag = request.context.tags[0] %>
        % if can_be_approved:
          <form class="tile2" action="${request.route_path("directory_tag_approve", type=current_tag.type, name=current_tag.url_name)}" method="post">
            <h3>Not approved</h3>
            <p class="middle_actions"><button type="submit">Approve</button></p>
          </form>
        % endif
        % if not synonyms:
          <form class="tile2" action="${request.route_path("directory_tag_make_synonym", type=current_tag.type, name=current_tag.url_name)}" method="post">
            <h3>Make this a synonym</h3>
            <p><select name="tag_type" required>
              <option value=""></option>
              % for tag_type in Tag.type.type.enums:
                <option value="${tag_type}">${tag_type.replace("_", " ")}</option>
              % endfor
            </select><input type="text" name="name" maxlength="100" required><button type="submit">Save</button></p>
          </form>
        % endif
        <form class="tile2" action="${request.route_path("directory_tag_add_parent", type=current_tag.type, name=current_tag.url_name)}" method="post">
          <h3>Add a parent tag</h3>
          <p><select name="tag_type" required>
            <option value=""></option>
            % for tag_type in Tag.type.type.enums:
              <option value="${tag_type}">${tag_type.replace("_", " ")}</option>
            % endfor
          </select><input type="text" name="name" maxlength="100" required><button type="submit">Add</button></p>
        </form>
      % endif
      % if synonyms or parents or children:
        <section class="tile2">
          <h3>Related tags</h3>
          % if synonyms:
            <h4 class="request_tag_label">Tags with the same meaning</h4>
            <ul class="request_tags related">
              % for synonym in synonyms:
                <li>${synonym.type.replace("_", " ")}:${synonym.name}</li>
              % endfor
            </ul>
          % endif
          % if parents:
            <h4 class="request_tag_label">Parent tags</h4>
            <ul class="request_tags related">
              % for tag in parents:
                <li><a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}">${tag.type.replace("_", " ")}:${tag.name}</a></li>
              % endfor
            </ul>
          % endif
          % if children:
            <h4 class="request_tag_label">Child tags</h4>
            <ul class="request_tags related">
              % for tag in children:
                <li><a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}">${tag.type.replace("_", " ")}:${tag.name}</a></li>
              % endfor
            </ul>
          % endif
        </section>
      % endif
    % endif
    % if len(request.context.tags) > 1:
      <section class="tile2">
        <h3>Tags</h3>
        <ul>
          % for tag in request.context.tags:
            <li>
              ${tag.type.replace("_", " ")}:${tag.name}
              (<a href="${request.route_path("directory_tag", tag_string=",".join(_.tag_string for _ in request.context.tags if _ != tag))}">x</a>)
            </li>
          % endfor
        </ul>
      </section>
    % endif
    % if blacklisted_tags:
      % if len(request.context.tags) == 1:
        <p>This tag can't be shown because it's on your <a href="${request.route_path("directory_blacklist")}">blacklist</a>.</p>
      % else:
        <p>These tags can't be shown because one or more of them are on your <a href="${request.route_path("directory_blacklist")}">blacklist</a>.</p>
      % endif
    % elif not requests:
      % if len(request.context.tags) == 1:
      <p>There are no requests with this tag.</p>
      % else:
      <p>There are no requests with these tags.</p>
      % endif
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
<%block name="tag_links">
      % if tag_types and len(tag_types) > 1:
      <% current_tag = request.context.tags[0] %>
      <h3>Tag types</h3>
      <ul>
        % for other_tag in tag_types:
          % if other_tag.type == current_tag.type:
            <li>${other_tag.type.replace("_", " ")}</li>
          % else:
            <li><a href="${request.route_path("directory_tag", tag_string=other_tag.tag_string)}">${other_tag.type.replace("_", " ")}</a></li>
          % endif
        % endfor
      </ul>
      % endif
</%block>
