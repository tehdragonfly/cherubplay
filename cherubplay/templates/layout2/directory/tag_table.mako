<%inherit file="/layout2/base.mako" />\
<%block name="title">Tags - </%block>
<% from cherubplay.models import Tag %>
<h2>Tags</h2>
<main>
  <table class="tile2" width="100%">
    <thead>
      <tr>
        % for tag_type in Tag.type.type.python_type:
        <th>${tag_type.ui_value.capitalize()}</th>
        % endfor
      </tr>
    </thead>
    <tbody>
      % for row in rows:
      <tr>
        % for tag_type in Tag.type.type.python_type:
        % if tag_type in row:
        <td class="\
% if row[tag_type].synonym_id is not None:
synonym\
% elif not row[tag_type].approved:
unapproved\
% endif
">
          <a href="${request.route_path("directory_tag", tag_string=row[tag_type].tag_string)}">${row[tag_type].name}</a>
        </td>
        % else:
        <td></td>
        % endif
        % endfor
      </tr>
      % endfor
    </tbody>
  </table>
</main>
