<%inherit file="base.mako" />\
<%block name="heading">Error</%block>
<% from cherubplay.models import Tag %>
    <p>Sorry, you can't answer this prompt because you've already answered it recently.</p>
    <p>Please <a href="javascript:history.back(1);">go back</a> and choose another.</p>
