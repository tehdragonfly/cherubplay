<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">Suggest changes to "${request.context.tags[0].type.ui_value}:${request.context.tags[0].name}"</%block>
  <section class="tile2">
    <h3>Merge into another tag</h3>
  </section>
  <section class="tile2">
    <h3>Add a parent tag</h3>
  </section>
  <section class="tile2">
    <h3>Restrict to NSFW extreme</h3>
  </section>
