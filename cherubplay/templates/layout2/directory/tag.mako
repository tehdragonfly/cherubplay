<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">
  % if request.matched_route.name == "directory_yours_tag":
    Your requests
  % else:
    Requests
  % endif
  % if len(request.context.tags) == 1:
    tagged "${request.context.tags[0].type.ui_value}:${request.context.tags[0].name}"
  % else:
    with ${len(request.context.tags)} tags
  % endif
</%block>
    % if "error" in request.GET and request.GET["error"] == "circular_reference":
    <p>That tag can't be added as a parent because it's already a child of this tag.</p>
    % endif
    % if len(request.context.tags) == 1 and not "before" in request.GET:
      % if request.has_permission("directory.manage_tags"):
        <section class="tile2">
          <h3>Actions</h3>
          <% current_tag = request.context.tags[0] %>
          % if can_be_approved:
            <form action="${request.route_path("directory_tag_approve", type=current_tag.type.value, name=current_tag.url_name)}" method="post">
              <p>Not approved. <button type="submit">Approve</button></p>
            </form>
            <hr>
          % endif
          % if not synonyms:
            <form action="${request.route_path("directory_tag_make_synonym", type=current_tag.type.value, name=current_tag.url_name)}" method="post">
              <p><label>Make this a synonym</label>
                <select name="tag_type" required>
                  <option value=""></option>
                  % for tag_type in Tag.type.type.python_type:
                    <option value="${tag_type.value}">${tag_type.ui_value}</option>
                  % endfor
                </select><input type="text" name="name" maxlength="100" required><button type="submit">Save</button>
              </p>
            </form>
            <hr>
          % endif
          <form action="${request.route_path("directory_tag_add_parent", type=current_tag.type.value, name=current_tag.url_name)}" method="post">
            <p><label>Add a parent tag:</label>
              <select name="tag_type" required>
                <option value=""></option>
                % for tag_type in Tag.type.type.python_type:
                  <option value="${tag_type.value}">${tag_type.ui_value}</option>
                % endfor
              </select><input type="text" name="name" maxlength="100" required><button type="submit">Add</button>
            </p>
          </form>
          <hr>
          % if current_tag.bump_maturity:
            <form action="${request.route_path("directory_tag_bump_maturity", type=current_tag.type.value, name=current_tag.url_name)}" method="post">
              <p><button type="submit">Disable maturity bumping</button></p>
            </form>
          % else:
            <form action="${request.route_path("directory_tag_bump_maturity", type=current_tag.type.value, name=current_tag.url_name)}" method="post">
              <input type="hidden" name="bump_maturity" value="on">
              <p><button type="submit">Enable maturity bumping</button></p>
            </form>
          % endif
        </section>
      % endif
      % if synonyms or parents or children:
        <section class="tile2">
          <h3>Related tags</h3>
          % if synonyms:
            <h4 class="request_tag_label">Tags with the same meaning</h4>
            <ul class="request_tags related">
              % for synonym in synonyms:
                <li>${synonym.type.ui_value}:${synonym.name}</li>
              % endfor
            </ul>
          % endif
          % if parents:
            <h4 class="request_tag_label">Parent tags</h4>
            <ul class="request_tags related">
              % for tag in parents:
                <li><a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}">${tag.type.ui_value}:${tag.name}</a></li>
              % endfor
            </ul>
          % endif
          % if children:
            <h4 class="request_tag_label">Child tags</h4>
            <ul class="request_tags related">
              % for tag in children:
                <li><a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}">${tag.type.ui_value}:${tag.name}</a></li>
              % endfor
            </ul>
          % endif
        </section>
      % endif
    % endif
    % if len(request.context.tags) > 1:
      <section class="tile2">
        <h3>Tags</h3>
        <ul class="tag_list">
          % for tag in request.context.tags:
            <li>
              <div class="actions">
                <div class="left">
                  ${tag.type.ui_value}:${tag.name}
                  (<a href="${request.route_path("directory_tag", tag_string=",".join(_.tag_string for _ in request.context.tags if _ != tag))}">x</a>)
                </div>
                <div class="right">
                  <form action="${request.route_path("directory_blacklist_add")}" method="post">
                    <input type="hidden" name="tag_type" value="${tag.type.value}">
                    <input type="hidden" name="name" value="${tag.name}">
                    <button type="submit">Add to blacklist</button>
                  </form>
                </div>
              </div>
            </li>
          % endfor
        </ul>
      </section>
    % endif
    % if not requests and blacklisted_tags:
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
      % if len(request.context.tags) < 5:
        <h3>Add to search</h3>
        <form class="directory_search_form" action="${request.route_path("directory_tag_search", tag_string=request.matchdict["tag_string"])}" method="get" data-autocomplete-path="${request.route_path("directory_tag_search_autocomplete", tag_string=request.matchdict["tag_string"])}">
          <div class="tag_input single">
            <input type="text" class="directory_search full" name="name" maxlength="100" placeholder="Look up a tag..." required>
          </div>
          <button>Search</button>
        </form>
      % endif
      % if tag_types and len(tag_types) > 1:
      <% current_tag = request.context.tags[0] %>
      <h3>Tag types</h3>
      <ul>
        % for other_tag in tag_types:
          % if other_tag.type == current_tag.type:
            <li>${other_tag.type.ui_value}</li>
          % else:
            <li><a href="${request.route_path("directory_tag", tag_string=other_tag.tag_string)}">${other_tag.type.ui_value}</a></li>
          % endif
        % endfor
      </ul>
      % endif
      % if len(request.context.tags) == 1 and not blacklisted_tags:
        <h3>Blacklist</h3>
        <form action="${request.route_path("directory_blacklist_add")}" method="post">
          <input type="hidden" name="tag_type" value="${request.context.tags[0].type.value}">
          <input type="hidden" name="name" value="${request.context.tags[0].name}">
          <ul><li><button type="submit">Add to blacklist</button></li></ul>
        </form>
      % endif
      % if "tag_suggestions" in request.user.flags and len(request.context.tags) == 1:
        <h3>Suggestions</h3>
        <ul>
          <li><a href="${request.route_path("directory_tag_suggest", type=request.context.tags[0].type.value, name=request.context.tags[0].url_name)}">Suggest changes to this tag</a></li>
        </ul>
      % endif

</%block>
