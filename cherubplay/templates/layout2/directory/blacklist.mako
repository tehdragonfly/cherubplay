<%inherit file="base.mako" />\
<%block name="heading">Blacklisted tags</%block>
    <section class="tile2">
      <ul>
        % for tag in tags:
        <li>${tag.tag.type.replace("_", " ")}:${tag.alias}</li>
        % endfor
      </ul>
    </section>
