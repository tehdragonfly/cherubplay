<%inherit file="base.mako" />\
<%block name="heading">Blacklisted tags</%block>
<% from cherubplay.models import Tag %>
    % if error == "invalid":
    <p><strong>${error_name}</strong> is not a valid ${error_tag_type}.</p>
    % endif
    <section class="tile2">
      <ul class="tag_list">
        <li>
          <form id="blacklist_add" action="${request.route_path("directory_blacklist_add")}" method="post">
            <select name="tag_type">
              % for tag_type in Tag.type.type.python_type:
              <option value="${tag_type.value}">${tag_type.ui_value}</option>
              % endfor
            </select>
            <select name="maturity_name">
              % for tag in maturity_tags:
              <option value="${tag.url_name}">${tag.name}</option>
              % endfor
            </select>
            <select name="type_name">
              % for tag in type_tags:
              <option value="${tag.url_name}">${tag.name}</option>
              % endfor
            </select>
            <input type="text" name="name" maxlength="100" required>
            <button type="submit">Add</button>
          </form>
        </li>
        % for tag in tags:
        <li>
          <form class="remove_form" action="${request.route_path("directory_blacklist_remove")}" method="post">
            <input type="hidden" name="tag_id" value="${tag.tag_id}">
            <button type="submit">Remove</button>
          </form>
          ${tag.tag.type.ui_value}:${tag.tag.name}
        </li>
        % endfor
      </ul>
    </section>
<%block name="scripts">
${parent.scripts()}
<script>cherubplay.directory_blacklist();</script>
</%block>
