<%inherit file="base.mako" />\
<%block name="heading">Blacklisted tags</%block>
<% from cherubplay.models import Tag %>
<% from cherubplay.models.enums import TagType %>
    % if error == "invalid":
    <p><strong>${error_name}</strong> is not a valid ${error_tag_type}.</p>
    % endif
    <section class="tile2">
      <ul class="tag_list">
        % if "shutdown.directory" not in request.registry.settings:
        <li>
          <form id="blacklist_add" action="${request.route_path("directory_blacklist_add")}" method="post">
            <select name="tag_type">
              % for tag_type in Tag.type.type.python_type:
                % if (tag_type == TagType.maturity and not maturity_tags) or (tag_type == TagType.type and not type_tags):
                  <% pass %>
                % else:
                  <option value="${tag_type.value}">${tag_type.ui_value}</option>
                % endif
              % endfor
            </select>
            % if maturity_tags:
              <select name="maturity_name">
                % for tag in maturity_tags:
                  <option value="${tag.url_name}">${tag.name}</option>
                % endfor
              </select>
            % endif
            % if type_tags:
              <select name="type_name">
                % for tag in type_tags:
                  <option value="${tag.url_name}">${tag.name}</option>
                % endfor
              </select>
            % endif
            <input type="text" name="name" maxlength="100" required>
            <button type="submit">Add</button>
          </form>
        </li>
        % endif
        % if tags:
        % for tag in tags:
        <li>
          % if "shutdown.directory" not in request.registry.settings:
            % if not request.user.show_nsfw and tag.type == TagType.maturity and tag.name != "Safe for work":
              <form class="remove_form" action="${request.route_path("directory_blacklist_remove")}" method="post">
                <input type="hidden" name="tag_id" value="${tag.id}">
                <button type="submit">Remove</button>
              </form>
            % endif
          % endif
          ${tag.type.ui_value}:${tag.name}
        </li>
        % endfor
        % else:
        <li>Your blacklist is empty.</li>
        % endif
      </ul>
    </section>
<%block name="scripts">
${parent.scripts()}
<script>cherubplay.directory_blacklist();</script>
</%block>
