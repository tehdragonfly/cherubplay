<%inherit file="base.mako" />\
<%block name="heading">Blacklisted tags</%block>
<% from cherubplay.models import Tag %>
    % if error == "invalid":
    <p><strong>${error_alias}</strong> is not a valid ${error_tag_type}.</p>
    % endif
    <section class="tile2">
      <ul id="blacklist">
        % for tag in tags:
        <li>
          <form class="remove_form" action="${request.route_path("directory_blacklist_remove")}" method="post">
            <input type="hidden" name="tag_id" value="${tag.tag_id}">
            <button type="submit">Remove</button>
          </form>
          ${tag.tag.type.replace("_", " ")}:${tag.alias}
        </li>
        % endfor
        <li>
          <form action="${request.route_path("directory_blacklist_add")}" method="post">
            <select name="tag_type">
              % for tag_type in Tag.type.type.enums:
              <option value="${tag_type}">${tag_type.replace("_", " ")}</option>
              % endfor
            </select>
            <input type="text" name="alias" maxlength="100" required>
            <button type="submit">Add</button>
          </form>
        </li>
      </ul>
    </section>
