<%inherit file="base.mako" />\
<%block name="heading">User connections</%block>
    <section class="tile2">
      <ul class="tag_list">
        % for connection in connections:
          <li>${connection.to.username}</li>
        % endfor
      </ul>
    </section>